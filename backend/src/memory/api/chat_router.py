"""
Enhanced chat router with memory integration.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
import requests

from .models import ChatRequest, ChatResponse, ChatMessage
from ..models import Conversation, Message, MessageRole
from ..services.memory_service_factory import get_memory_service
from ..interfaces import MemoryServiceInterface

logger = logging.getLogger(__name__)

# Create the chat router
chat_router = APIRouter(
    prefix="/memory",
    tags=["chat"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request"},
        503: {"description": "Service unavailable"}
    }
)


async def get_memory_service_dependency() -> MemoryServiceInterface:
    """Dependency to get the memory service instance."""
    try:
        service = get_memory_service()
        await service.initialize()
        return service
    except Exception as e:
        logger.error(f"Failed to initialize memory service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service unavailable"
        )


@chat_router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with memory integration",
    description="Enhanced chat endpoint that automatically integrates conversation context and stores interactions in memory."
)
async def chat_with_memory(
    request: ChatRequest,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> ChatResponse:
    """
    Chat endpoint with full memory integration.
    
    This endpoint:
    1. Retrieves conversation context for the user
    2. Enhances the prompt with relevant context
    3. Processes the chat request
    4. Stores the conversation in memory
    5. Returns the response with context information
    """
    try:
        # Retrieve conversation context if requested
        context_text = ""
        context_summary = None
        
        if request.include_context:
            try:
                context = await memory_service.retrieve_context(
                    request.user_id, 
                    request.context_limit
                )
                if context:
                    context_text = context.get_context_text()
                    context_summary = context.context_summary
                    logger.debug(f"Retrieved context for user {request.user_id}: {len(context_text)} chars")
            except Exception as e:
                logger.warning(f"Failed to retrieve context for user {request.user_id}: {e}")
                # Continue without context
        
        # Create enhanced prompt with context
        enhanced_message = _create_enhanced_prompt(request.message, context_text)
        
        # Make the chat request to the LLM
        chat_response = await _process_chat_request(enhanced_message)
        
        # Store the conversation in memory
        conversation_id = None
        try:
            conversation_id = await _store_chat_interaction(
                memory_service,
                request.user_id,
                request.message,  # Store original message, not enhanced
                chat_response
            )
        except Exception as e:
            logger.error(f"Failed to store conversation for user {request.user_id}: {e}")
            # Continue without storing - don't fail the chat
        
        return ChatResponse(
            reply=chat_response,
            context_used=bool(context_text),
            context_summary=context_summary,
            conversation_id=conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat request failed for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}"
        )


@chat_router.post(
    "/chat/simple",
    response_model=dict,
    summary="Simple chat with optional memory",
    description="Simplified chat endpoint that optionally uses memory based on request parameters."
)
async def simple_chat_with_memory(
    user_id: str,
    message: str,
    use_memory: bool = True,
    memory_service: Optional[MemoryServiceInterface] = Depends(get_memory_service_dependency)
) -> dict:
    """
    Simplified chat endpoint with optional memory integration.
    
    This provides a simpler interface while still offering memory capabilities.
    """
    try:
        context_text = ""
        
        # Get context if memory is enabled and available
        if use_memory and memory_service:
            try:
                context = await memory_service.retrieve_context(user_id)
                if context:
                    context_text = context.get_context_text()
            except Exception as e:
                logger.warning(f"Memory retrieval failed, continuing without context: {e}")
        
        # Create enhanced prompt
        enhanced_message = _create_enhanced_prompt(message, context_text) if context_text else message
        
        # Process chat request
        reply = await _process_chat_request(enhanced_message)
        
        # Store conversation if memory is enabled
        if use_memory and memory_service:
            try:
                await _store_chat_interaction(memory_service, user_id, message, reply)
            except Exception as e:
                logger.warning(f"Failed to store conversation: {e}")
        
        return {
            "reply": reply,
            "memory_used": use_memory and bool(context_text)
        }
        
    except Exception as e:
        logger.error(f"Simple chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


async def _process_chat_request(message: str) -> str:
    """Process the chat request with the LLM."""
    try:
        payload = {
            "model": "gpt-oss:20b",
            "prompt": message
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate", 
            json=payload, 
            stream=False,
            timeout=30  # Add timeout
        )
        
        if response.status_code == 200:
            content = response.json()
            return content.get("response", "No response")
        else:
            logger.error(f"LLM request failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM service error: {response.status_code}"
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM request exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM service unavailable"
        )


def _create_enhanced_prompt(user_message: str, context_text: str) -> str:
    """Create an enhanced prompt with conversation context."""
    if not context_text or not context_text.strip():
        return user_message
    
    # Create a more sophisticated context injection
    enhanced_prompt = f"""You are continuing a conversation. Here is the relevant context from our previous interactions:

{context_text}

---

Current user message: {user_message}

Please respond naturally, taking into account our conversation history when relevant."""
    
    return enhanced_prompt


async def _store_chat_interaction(
    memory_service: MemoryServiceInterface,
    user_id: str,
    user_message: str,
    assistant_reply: str
) -> str:
    """Store the chat interaction in memory and return conversation ID."""
    
    # Create conversation object
    conversation_id = str(uuid.uuid4())
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
        messages=[
            Message(
                id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=user_message,
                timestamp=datetime.now(timezone.utc)
            ),
            Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=assistant_reply,
                timestamp=datetime.now(timezone.utc)
            )
        ],
        tags=["chat_interaction"]
    )
    
    # Store the conversation
    await memory_service.store_conversation(user_id, conversation)
    logger.debug(f"Stored chat interaction {conversation_id} for user {user_id}")
    
    return conversation_id


# Health check for chat functionality
@chat_router.get(
    "/chat/health",
    summary="Chat service health check",
    description="Check the health of the chat service including LLM connectivity and memory integration."
)
async def chat_health_check(
    memory_service: Optional[MemoryServiceInterface] = Depends(get_memory_service_dependency)
) -> dict:
    """Check the health of chat services."""
    health_status = {
        "chat_service": "healthy",
        "llm_service": "unknown",
        "memory_integration": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check LLM service
    try:
        test_payload = {
            "model": "gpt-oss:20b",
            "prompt": "test"
        }
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=test_payload,
            timeout=5
        )
        health_status["llm_service"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        health_status["llm_service"] = f"unhealthy: {str(e)}"
    
    # Check memory integration
    if memory_service:
        try:
            memory_health = await memory_service.health_check()
            health_status["memory_integration"] = memory_health.get("memory_service", "unknown")
        except Exception as e:
            health_status["memory_integration"] = f"unhealthy: {str(e)}"
    else:
        health_status["memory_integration"] = "unavailable"
    
    return health_status