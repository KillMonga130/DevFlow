"""
Middleware for integrating memory functionality with chat endpoints.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..models import Conversation, Message, MessageRole
from ..services.memory_service_factory import get_memory_service
from ..interfaces import MemoryServiceInterface

logger = logging.getLogger(__name__)


class ChatMemoryMiddleware(BaseHTTPMiddleware):
    """
    Middleware that integrates memory functionality with chat endpoints.
    
    This middleware:
    1. Intercepts chat requests to inject conversation context
    2. Stores chat interactions in the memory system
    3. Provides transparent memory functionality without breaking existing flows
    """
    
    def __init__(
        self,
        app,
        memory_service: Optional[MemoryServiceInterface] = None,
        enabled: bool = True,
        context_injection_enabled: bool = True,
        storage_enabled: bool = True,
        fallback_on_error: bool = True
    ):
        """
        Initialize the chat memory middleware.
        
        Args:
            app: FastAPI application instance
            memory_service: Optional memory service instance
            enabled: Whether memory functionality is enabled
            context_injection_enabled: Whether to inject context into chat requests
            storage_enabled: Whether to store conversations
            fallback_on_error: Whether to continue on memory service errors
        """
        super().__init__(app)
        self._memory_service = memory_service
        self._enabled = enabled
        self._context_injection_enabled = context_injection_enabled
        self._storage_enabled = storage_enabled
        self._fallback_on_error = fallback_on_error
        self._initialized = False
        
        logger.info(f"ChatMemoryMiddleware initialized (enabled={enabled})")
    
    async def _get_memory_service(self) -> Optional[MemoryServiceInterface]:
        """Get the memory service instance."""
        if not self._memory_service:
            try:
                self._memory_service = get_memory_service()
                await self._memory_service.initialize()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize memory service: {e}")
                if not self._fallback_on_error:
                    raise
                return None
        
        return self._memory_service
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and response, adding memory functionality.
        """
        # Skip if memory is disabled
        if not self._enabled:
            return await call_next(request)
        
        # Only process chat endpoints
        if not self._is_chat_endpoint(request):
            return await call_next(request)
        
        try:
            # Get memory service
            memory_service = await self._get_memory_service()
            if not memory_service:
                logger.warning("Memory service unavailable, proceeding without memory")
                return await call_next(request)
            
            # Process the chat request with memory integration
            return await self._process_chat_with_memory(request, call_next, memory_service)
            
        except Exception as e:
            logger.error(f"Error in chat memory middleware: {e}")
            if self._fallback_on_error:
                logger.warning("Falling back to standard chat processing")
                return await call_next(request)
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Memory service error", "detail": str(e)}
                )
    
    def _is_chat_endpoint(self, request: Request) -> bool:
        """Check if the request is for a chat endpoint."""
        return (
            request.url.path == "/chat" or 
            request.url.path.startswith("/chat/") or
            request.url.path == "/memory/chat"
        )
    
    async def _process_chat_with_memory(
        self,
        request: Request,
        call_next: Callable,
        memory_service: MemoryServiceInterface
    ) -> Response:
        """Process chat request with memory integration."""
        
        # Extract request data
        request_data = await self._extract_request_data(request)
        if not request_data:
            return await call_next(request)
        
        user_id = request_data.get("user_id")
        user_message = request_data.get("user_input") or request_data.get("message")
        
        if not user_id or not user_message:
            logger.warning("Missing user_id or message in chat request")
            return await call_next(request)
        
        # Retrieve conversation context if enabled
        context_text = ""
        if self._context_injection_enabled:
            try:
                context = await memory_service.retrieve_context(user_id)
                context_text = context.get_context_text() if context else ""
                logger.debug(f"Retrieved context for user {user_id}: {len(context_text)} chars")
            except Exception as e:
                logger.warning(f"Failed to retrieve context for user {user_id}: {e}")
        
        # Modify request to include context
        modified_request = await self._inject_context_into_request(
            request, user_message, context_text
        )
        
        # Process the chat request
        response = await call_next(modified_request)
        
        # Store the conversation if enabled and response is successful
        if self._storage_enabled and response.status_code == 200:
            try:
                response_data = await self._extract_response_data(response)
                assistant_reply = response_data.get("reply", "")
                
                if assistant_reply:
                    await self._store_conversation(
                        memory_service, user_id, user_message, assistant_reply
                    )
            except Exception as e:
                logger.error(f"Failed to store conversation for user {user_id}: {e}")
        
        return response
    
    async def _extract_request_data(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract data from the request."""
        try:
            if request.method == "POST":
                # Clone the request body for processing
                body = await request.body()
                if body:
                    import json
                    return json.loads(body.decode())
            return None
        except Exception as e:
            logger.error(f"Failed to extract request data: {e}")
            return None
    
    async def _inject_context_into_request(
        self,
        request: Request,
        user_message: str,
        context_text: str
    ) -> Request:
        """Inject conversation context into the chat request."""
        if not context_text:
            return request
        
        try:
            # Create enhanced prompt with context
            enhanced_message = self._create_enhanced_prompt(user_message, context_text)
            
            # Create new request body
            import json
            original_body = await request.body()
            original_data = json.loads(original_body.decode()) if original_body else {}
            
            # Update the message with context
            if "user_input" in original_data:
                original_data["user_input"] = enhanced_message
            elif "message" in original_data:
                original_data["message"] = enhanced_message
            
            # Create new request with modified body
            new_body = json.dumps(original_data).encode()
            
            # Create a new request object with the modified body
            from starlette.requests import Request as StarletteRequest
            
            scope = request.scope.copy()
            scope["body"] = new_body
            
            async def receive():
                return {"type": "http.request", "body": new_body}
            
            new_request = StarletteRequest(scope, receive)
            return new_request
            
        except Exception as e:
            logger.error(f"Failed to inject context into request: {e}")
            return request
    
    def _create_enhanced_prompt(self, user_message: str, context_text: str) -> str:
        """Create an enhanced prompt with conversation context."""
        if not context_text.strip():
            return user_message
        
        enhanced_prompt = f"""Previous conversation context:
{context_text}

Current message: {user_message}

Please respond considering the conversation history above."""
        
        return enhanced_prompt
    
    async def _extract_response_data(self, response: Response) -> Dict[str, Any]:
        """Extract data from the response."""
        try:
            if hasattr(response, 'body'):
                import json
                body_bytes = response.body
                if body_bytes:
                    return json.loads(body_bytes.decode())
            return {}
        except Exception as e:
            logger.error(f"Failed to extract response data: {e}")
            return {}
    
    async def _store_conversation(
        self,
        memory_service: MemoryServiceInterface,
        user_id: str,
        user_message: str,
        assistant_reply: str
    ) -> None:
        """Store the conversation in the memory system."""
        try:
            # Create conversation object
            conversation = Conversation(
                id=str(uuid.uuid4()),
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
                ]
            )
            
            # Store the conversation
            await memory_service.store_conversation(user_id, conversation)
            logger.debug(f"Stored conversation {conversation.id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            raise


class MemoryEnabledChatMiddleware(BaseHTTPMiddleware):
    """
    Simplified middleware that adds memory capabilities to existing chat endpoints.
    
    This is a lighter version that focuses on transparent integration.
    """
    
    def __init__(self, app, fallback_on_error: bool = True):
        super().__init__(app)
        self._fallback_on_error = fallback_on_error
        self._memory_service = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add memory headers and context to chat requests."""
        
        # Add memory-related headers
        if self._is_chat_request(request):
            # Add header to indicate memory is available
            request.headers.__dict__.setdefault("mutable", True)
            if hasattr(request.headers, "_list"):
                request.headers._list.append((b"x-memory-enabled", b"true"))
        
        response = await call_next(request)
        
        # Add memory-related response headers
        if self._is_chat_request(request) and response.status_code == 200:
            response.headers["X-Memory-Enabled"] = "true"
            response.headers["X-Memory-Version"] = "1.0"
        
        return response
    
    def _is_chat_request(self, request: Request) -> bool:
        """Check if this is a chat request."""
        return request.url.path in ["/chat", "/memory/chat"]