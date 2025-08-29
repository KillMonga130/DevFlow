"""
Integration tests for chat system with memory functionality.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from backend.main import app
from backend.src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext
)

client = TestClient(app)


@pytest.fixture
def sample_context():
    """Create a sample conversation context."""
    return ConversationContext(
        user_id="test-user-123",
        context_summary="Previous conversation about API development",
        recent_messages=[
            Message(
                id="msg-1",
                role=MessageRole.USER,
                content="Tell me about APIs",
                timestamp=datetime.now(timezone.utc)
            ),
            Message(
                id="msg-2", 
                role=MessageRole.ASSISTANT,
                content="APIs are interfaces that allow different software applications to communicate.",
                timestamp=datetime.now(timezone.utc)
            )
        ]
    )


class TestChatMemoryIntegration:
    """Test chat endpoints with memory integration."""
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_memory_chat_with_context(self, mock_requests, mock_get_service, sample_context):
        """Test memory-enabled chat with context retrieval."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.retrieve_context = AsyncMock(return_value=sample_context)
        mock_service.store_conversation = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {"response": "Based on our previous discussion about APIs, here's more information..."}
        mock_requests.return_value = mock_llm_response
        
        # Make chat request
        request_data = {
            "user_id": "test-user-123",
            "message": "Can you tell me more?",
            "include_context": True
        }
        
        response = client.post("/memory/chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert data["context_used"] is True
        assert data["context_summary"] == "Previous conversation about API development"
        assert data["conversation_id"] is not None
        
        # Verify memory service was called
        mock_service.retrieve_context.assert_called_once_with("test-user-123", None)
        mock_service.store_conversation.assert_called_once()
        
        # Verify LLM was called with enhanced prompt
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        prompt = call_args[1]["json"]["prompt"]
        assert "Previous conversation" in prompt
        assert "Can you tell me more?" in prompt
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_memory_chat_without_context(self, mock_requests, mock_get_service):
        """Test memory-enabled chat without context."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.store_conversation = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {"response": "Hello! How can I help you?"}
        mock_requests.return_value = mock_llm_response
        
        # Make chat request without context
        request_data = {
            "user_id": "test-user-123",
            "message": "Hello",
            "include_context": False
        }
        
        response = client.post("/memory/chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Hello! How can I help you?"
        assert data["context_used"] is False
        assert data["context_summary"] is None
        
        # Verify conversation was still stored
        mock_service.store_conversation.assert_called_once()
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_simple_chat_with_memory(self, mock_requests, mock_get_service, sample_context):
        """Test simple chat endpoint with memory."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.retrieve_context = AsyncMock(return_value=sample_context)
        mock_service.store_conversation = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {"response": "Sure, I can help with that!"}
        mock_requests.return_value = mock_llm_response
        
        # Make simple chat request
        params = {
            "user_id": "test-user-123",
            "message": "Help me with something",
            "use_memory": True
        }
        
        response = client.post("/memory/chat/simple", params=params)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Sure, I can help with that!"
        assert data["memory_used"] is True
        
        # Verify memory operations
        mock_service.retrieve_context.assert_called_once()
        mock_service.store_conversation.assert_called_once()
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_simple_chat_without_memory(self, mock_requests, mock_get_service):
        """Test simple chat endpoint without memory."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {"response": "Hello there!"}
        mock_requests.return_value = mock_llm_response
        
        # Make simple chat request without memory
        params = {
            "user_id": "test-user-123",
            "message": "Hello",
            "use_memory": False
        }
        
        response = client.post("/memory/chat/simple", params=params)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Hello there!"
        assert data["memory_used"] is False
        
        # Verify memory operations were not called
        mock_service.retrieve_context.assert_not_called()
        mock_service.store_conversation.assert_not_called()
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_chat_with_memory_service_failure(self, mock_requests, mock_get_service):
        """Test chat continues when memory service fails."""
        # Mock memory service that fails
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.retrieve_context = AsyncMock(side_effect=Exception("Memory service error"))
        mock_service.store_conversation = AsyncMock(side_effect=Exception("Storage error"))
        mock_get_service.return_value = mock_service
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        mock_llm_response.json.return_value = {"response": "I can still help you!"}
        mock_requests.return_value = mock_llm_response
        
        # Make chat request
        request_data = {
            "user_id": "test-user-123",
            "message": "Hello",
            "include_context": True
        }
        
        response = client.post("/memory/chat", json=request_data)
        
        # Verify response - should succeed despite memory failures
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "I can still help you!"
        assert data["context_used"] is False  # No context due to failure
        assert data["conversation_id"] is None  # No storage due to failure
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    @patch('requests.post')
    def test_chat_with_llm_failure(self, mock_requests, mock_get_service):
        """Test chat handles LLM service failures."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Mock LLM failure
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 500
        mock_llm_response.text = "Internal server error"
        mock_requests.return_value = mock_llm_response
        
        # Make chat request
        request_data = {
            "user_id": "test-user-123",
            "message": "Hello"
        }
        
        response = client.post("/memory/chat", json=request_data)
        
        # Verify error response
        assert response.status_code == 502  # Bad Gateway
        data = response.json()
        assert "LLM service error" in data["detail"]
    
    @patch('backend.src.memory.api.chat_router.get_memory_service')
    def test_chat_health_check(self, mock_get_service):
        """Test chat health check endpoint."""
        # Mock memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.health_check = AsyncMock(return_value={"memory_service": "healthy"})
        mock_get_service.return_value = mock_service
        
        # Mock LLM health check
        with patch('requests.post') as mock_requests:
            mock_llm_response = MagicMock()
            mock_llm_response.status_code = 200
            mock_requests.return_value = mock_llm_response
            
            response = client.get("/memory/chat/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["chat_service"] == "healthy"
            assert data["llm_service"] == "healthy"
            assert data["memory_integration"] == "healthy"
    
    def test_original_chat_endpoint_still_works(self):
        """Test that the original chat endpoint continues to work."""
        with patch('requests.post') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Original chat works!"}
            mock_requests.return_value = mock_response
            
            response = client.post("/chat", json={"user_input": "Hello"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == "Original chat works!"
    
    def test_memory_middleware_headers(self):
        """Test that memory middleware adds appropriate headers."""
        with patch('requests.post') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Hello!"}
            mock_requests.return_value = mock_response
            
            response = client.post("/chat", json={"user_input": "Hello"})
            
            # Check for memory-related headers
            assert response.headers.get("X-Memory-Enabled") == "true"
            assert response.headers.get("X-Memory-Version") == "1.0"


class TestChatMemoryMiddleware:
    """Test the chat memory middleware functionality."""
    
    def test_middleware_identifies_chat_endpoints(self):
        """Test that middleware correctly identifies chat endpoints."""
        from backend.src.memory.middleware.chat_memory_middleware import MemoryEnabledChatMiddleware
        
        # Create a mock request
        class MockRequest:
            def __init__(self, path):
                self.url = type('obj', (object,), {'path': path})
        
        middleware = MemoryEnabledChatMiddleware(None)
        
        # Test chat endpoint identification
        assert middleware._is_chat_request(MockRequest("/chat")) is True
        assert middleware._is_chat_request(MockRequest("/memory/chat")) is True
        assert middleware._is_chat_request(MockRequest("/other")) is False
        assert middleware._is_chat_request(MockRequest("/memory/conversations")) is False
    
    @patch('backend.src.memory.middleware.chat_memory_middleware.get_memory_service')
    def test_middleware_context_injection(self, mock_get_service):
        """Test middleware context injection functionality."""
        from backend.src.memory.middleware.chat_memory_middleware import ChatMemoryMiddleware
        
        # This would require more complex mocking of FastAPI request/response cycle
        # For now, we test the core logic components
        middleware = ChatMemoryMiddleware(None, enabled=True)
        
        # Test enhanced prompt creation
        user_message = "What's the weather like?"
        context_text = "Previous conversation: User asked about the weather yesterday."
        
        enhanced_prompt = middleware._create_enhanced_prompt(user_message, context_text)
        
        assert "Previous conversation context:" in enhanced_prompt
        assert user_message in enhanced_prompt
        assert context_text in enhanced_prompt
    
    def test_middleware_disabled_mode(self):
        """Test middleware behavior when disabled."""
        from backend.src.memory.middleware.chat_memory_middleware import ChatMemoryMiddleware
        
        middleware = ChatMemoryMiddleware(None, enabled=False)
        assert middleware._enabled is False
        
        # When disabled, middleware should pass through requests unchanged
        # This would require integration testing to fully verify