"""
Unit tests for chat memory middleware.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from src.memory.middleware.chat_memory_middleware import (
    ChatMemoryMiddleware, MemoryEnabledChatMiddleware
)
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext
)
from src.memory.interfaces import MemoryServiceInterface


class TestChatMemoryMiddleware:
    """Test cases for ChatMemoryMiddleware class."""
    
    @pytest.fixture
    def mock_memory_service(self):
        """Create a mock memory service for testing."""
        service = AsyncMock(spec=MemoryServiceInterface)
        service.retrieve_context = AsyncMock()
        service.store_conversation = AsyncMock()
        service.initialize = AsyncMock()
        return service
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app for testing."""
        app = FastAPI()
        
        @app.post("/chat")
        async def chat_endpoint(request: Request):
            body = await request.body()
            return JSONResponse({"response": "Hello from chat", "body": body.decode()})
        
        @app.get("/health")
        async def health_endpoint():
            return JSONResponse({"status": "ok"})
        
        return app
    
    @pytest.fixture
    def middleware(self, mock_memory_service):
        """Create middleware instance for testing."""
        return ChatMemoryMiddleware(
            app=None,  # Will be set when adding to app
            memory_service=mock_memory_service,
            enabled=True,
            context_injection_enabled=True,
            storage_enabled=True,
            fallback_on_error=True
        )
    
    @pytest.fixture
    def app_with_middleware(self, app, middleware):
        """Create app with middleware for testing."""
        app.add_middleware(ChatMemoryMiddleware, memory_service=middleware.memory_service)
        return app
    
    def test_middleware_initialization_default(self):
        """Test middleware initialization with default parameters."""
        middleware = ChatMemoryMiddleware(app=None)
        
        assert middleware._enabled is True
        assert middleware._context_injection_enabled is True
        assert middleware._storage_enabled is True
        assert middleware._fallback_on_error is True
        assert middleware._memory_service is None  # Will be created lazily
    
    def test_middleware_initialization_custom(self, mock_memory_service):
        """Test middleware initialization with custom parameters."""
        middleware = ChatMemoryMiddleware(
            app=None,
            memory_service=mock_memory_service,
            enabled=False,
            context_injection_enabled=False,
            storage_enabled=False,
            fallback_on_error=False
        )
        
        assert middleware._enabled is False
        assert middleware._context_injection_enabled is False
        assert middleware._storage_enabled is False
        assert middleware._fallback_on_error is False
        assert middleware._memory_service == mock_memory_service
    
    @pytest.mark.asyncio
    async def test_middleware_disabled(self):
        """Test that middleware passes through when disabled."""
        # Create middleware with disabled state
        disabled_middleware = ChatMemoryMiddleware(
            app=None,
            enabled=False
        )
        
        # Mock request and call_next
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"test": "response"})
        call_next.return_value = expected_response
        
        # Process request
        response = await disabled_middleware.dispatch(request, call_next)
        
        # Should pass through without modification
        assert response == expected_response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_middleware_non_chat_endpoint(self, middleware):
        """Test middleware behavior on non-chat endpoints."""
        request = Mock()
        request.url.path = "/health"
        request.method = "GET"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"status": "ok"})
        call_next.return_value = expected_response
        
        response = await middleware.dispatch(request, call_next)
        
        # Should pass through without memory processing
        assert response == expected_response
        call_next.assert_called_once_with(request)
        middleware._memory_service.retrieve_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_chat_endpoint_success(self, middleware):
        """Test successful middleware processing on chat endpoint."""
        # Mock request
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        # Mock call_next
        call_next = AsyncMock()
        expected_response = JSONResponse({"response": "Hello back"})
        expected_response.status_code = 200
        call_next.return_value = expected_response
        
        # Mock request data extraction to return valid data
        with patch.object(middleware, '_extract_request_data') as mock_extract:
            mock_extract.return_value = {"user_id": "user123", "message": "Hello"}
            
            # Mock context retrieval
            mock_context = Mock()
            mock_context.get_context_text.return_value = "Previous context"
            middleware._memory_service.retrieve_context.return_value = mock_context
            
            # Mock context injection
            with patch.object(middleware, '_inject_context_into_request') as mock_inject:
                mock_inject.return_value = request
                
                # Mock response data extraction
                with patch.object(middleware, '_extract_response_data') as mock_response_extract:
                    mock_response_extract.return_value = {"reply": "Hello back"}
                    
                    # Mock conversation storage
                    with patch.object(middleware, '_store_conversation') as mock_store:
                        # Process request
                        response = await middleware.dispatch(request, call_next)
                        
                        # Should retrieve context and store conversation
                        middleware._memory_service.retrieve_context.assert_called_once_with("user123")
                        mock_store.assert_called_once()
                        
                        assert response == expected_response
    
    @pytest.mark.asyncio
    async def test_middleware_memory_service_error_with_fallback(self, middleware):
        """Test middleware behavior when memory service fails with fallback enabled."""
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"response": "Hello back"})
        expected_response.status_code = 200
        call_next.return_value = expected_response
        
        # Mock request data extraction to return valid data
        with patch.object(middleware, '_extract_request_data') as mock_extract:
            mock_extract.return_value = {"user_id": "user123", "message": "Hello"}
            
            # Configure memory service to fail
            middleware._memory_service.retrieve_context.side_effect = Exception("Memory service error")
            
            # Should not raise exception due to fallback
            response = await middleware.dispatch(request, call_next)
            
            assert response == expected_response
            call_next.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_memory_service_error_no_fallback(self, middleware):
        """Test middleware behavior when memory service fails without fallback."""
        middleware._fallback_on_error = False
        
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        
        # Mock request data extraction to return valid data
        with patch.object(middleware, '_extract_request_data') as mock_extract:
            mock_extract.return_value = {"user_id": "user123", "message": "Hello"}
            
            # Configure memory service to fail
            middleware._memory_service.retrieve_context.side_effect = Exception("Memory service error")
            
            # Should return error response when fallback is disabled
            response = await middleware.dispatch(request, call_next)
            
            # Check that it's a JSONResponse with error status
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_middleware_context_injection_disabled(self, middleware):
        """Test middleware with context injection disabled."""
        middleware._context_injection_enabled = False
        
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"response": "Hello back"})
        expected_response.status_code = 200
        call_next.return_value = expected_response
        
        # Mock request data extraction to return valid data
        with patch.object(middleware, '_extract_request_data') as mock_extract:
            mock_extract.return_value = {"user_id": "user123", "message": "Hello"}
            
            # Mock context injection
            with patch.object(middleware, '_inject_context_into_request') as mock_inject:
                mock_inject.return_value = request
                
                # Mock response data extraction
                with patch.object(middleware, '_extract_response_data') as mock_response_extract:
                    mock_response_extract.return_value = {"reply": "Hello back"}
                    
                    # Mock conversation storage
                    with patch.object(middleware, '_store_conversation') as mock_store:
                        response = await middleware.dispatch(request, call_next)
                        
                        # Should not retrieve context when injection is disabled
                        middleware._memory_service.retrieve_context.assert_not_called()
                        
                        # But should still store conversation if storage is enabled
                        mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_storage_disabled(self, middleware):
        """Test middleware with storage disabled."""
        middleware._storage_enabled = False
        
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"response": "Hello back"})
        expected_response.status_code = 200
        call_next.return_value = expected_response
        
        # Mock request data extraction to return valid data
        with patch.object(middleware, '_extract_request_data') as mock_extract:
            mock_extract.return_value = {"user_id": "user123", "message": "Hello"}
            
            # Mock context retrieval
            mock_context = Mock()
            mock_context.get_context_text.return_value = "Previous context"
            middleware._memory_service.retrieve_context.return_value = mock_context
            
            # Mock context injection
            with patch.object(middleware, '_inject_context_into_request') as mock_inject:
                mock_inject.return_value = request
                
                # Mock conversation storage (should not be called)
                with patch.object(middleware, '_store_conversation') as mock_store:
                    response = await middleware.dispatch(request, call_next)
                    
                    # Should retrieve context but not store conversation
                    middleware._memory_service.retrieve_context.assert_called_once_with("user123")
                    mock_store.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_lazy_memory_service_creation(self):
        """Test that memory service is created lazily when not provided."""
        middleware = ChatMemoryMiddleware(app=None, memory_service=None)
        
        request = Mock()
        request.url.path = "/chat"
        request.method = "POST"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"response": "Hello back"})
        expected_response.status_code = 200
        call_next.return_value = expected_response
        
        with patch('src.memory.middleware.chat_memory_middleware.get_memory_service') as mock_get_service:
            mock_service = AsyncMock(spec=MemoryServiceInterface)
            mock_service.initialize = AsyncMock()
            mock_get_service.return_value = mock_service
            
            # Mock request data extraction to return None (no valid data)
            with patch.object(middleware, '_extract_request_data', return_value=None):
                response = await middleware.dispatch(request, call_next)
            
            # Should create memory service lazily
            mock_get_service.assert_called_once()
            assert middleware._memory_service == mock_service


class TestMemoryEnabledChatMiddleware:
    """Test cases for MemoryEnabledChatMiddleware class."""
    
    @pytest.fixture
    def memory_enabled_middleware(self):
        """Create MemoryEnabledChatMiddleware instance for testing."""
        return MemoryEnabledChatMiddleware(app=None, fallback_on_error=True)
    
    @pytest.mark.asyncio
    async def test_middleware_initialization(self, memory_enabled_middleware):
        """Test middleware initialization."""
        assert memory_enabled_middleware._fallback_on_error is True
        assert memory_enabled_middleware._memory_service is None
    
    def test_is_chat_request_true(self, memory_enabled_middleware):
        """Test _is_chat_request returns True for chat endpoints."""
        request = Mock()
        request.url.path = "/chat"
        
        assert memory_enabled_middleware._is_chat_request(request) is True
        
        request.url.path = "/memory/chat"
        assert memory_enabled_middleware._is_chat_request(request) is True
    
    def test_is_chat_request_false(self, memory_enabled_middleware):
        """Test _is_chat_request returns False for non-chat endpoints."""
        request = Mock()
        request.url.path = "/health"
        
        assert memory_enabled_middleware._is_chat_request(request) is False
        
        request.url.path = "/api/users"
        assert memory_enabled_middleware._is_chat_request(request) is False
    
    @pytest.mark.asyncio
    async def test_dispatch_non_chat_request(self, memory_enabled_middleware):
        """Test dispatch for non-chat requests."""
        request = Mock()
        request.url.path = "/health"
        
        call_next = AsyncMock()
        expected_response = JSONResponse({"status": "ok"})
        call_next.return_value = expected_response
        
        response = await memory_enabled_middleware.dispatch(request, call_next)
        
        assert response == expected_response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_dispatch_chat_request_adds_headers(self, memory_enabled_middleware):
        """Test dispatch adds memory headers to chat requests."""
        request = Mock()
        request.url.path = "/chat"
        
        call_next = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response
        
        result = await memory_enabled_middleware.dispatch(request, call_next)
        
        # Should add memory-related headers to response
        assert result.headers.get("X-Memory-Enabled") == "true"
        assert result.headers.get("X-Memory-Version") == "1.0"


class TestMiddlewareIntegration:
    """Integration tests for middleware with FastAPI."""
    
    def test_middleware_is_chat_endpoint(self):
        """Test _is_chat_endpoint method."""
        middleware = ChatMemoryMiddleware(app=None)
        
        # Test chat endpoints
        request = Mock()
        request.url.path = "/chat"
        assert middleware._is_chat_endpoint(request) is True
        
        request.url.path = "/chat/stream"
        assert middleware._is_chat_endpoint(request) is True
        
        request.url.path = "/memory/chat"
        assert middleware._is_chat_endpoint(request) is True
        
        # Test non-chat endpoints
        request.url.path = "/health"
        assert middleware._is_chat_endpoint(request) is False
        
        request.url.path = "/api/users"
        assert middleware._is_chat_endpoint(request) is False


if __name__ == "__main__":
    pytest.main([__file__])