"""
Tests for memory service API endpoints.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import app
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    SearchResult, UserDataExport, PrivacySettings, PrivacyMode,
    DataRetentionPolicy
)

client = TestClient(app)


@pytest.fixture
def sample_conversation():
    """Create a sample conversation for testing."""
    return Conversation(
        id="test-conv-123",
        user_id="test-user-123",
        timestamp=datetime.now(timezone.utc),
        messages=[
            Message(
                id="msg-1",
                role=MessageRole.USER,
                content="Hello, how are you?",
                timestamp=datetime.now(timezone.utc)
            ),
            Message(
                id="msg-2",
                role=MessageRole.ASSISTANT,
                content="I'm doing well, thank you for asking!",
                timestamp=datetime.now(timezone.utc)
            )
        ]
    )


@pytest.fixture
def sample_context():
    """Create a sample conversation context for testing."""
    return ConversationContext(
        user_id="test-user-123",
        context_summary="Previous conversation about greetings"
    )


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        SearchResult(
            conversation_id="test-conv-123",
            relevance_score=0.95,
            timestamp=datetime.now(timezone.utc),
            content_snippet="Hello, how are you?",
            topics=["greeting"]
        )
    ]


@pytest.fixture
def sample_privacy_settings():
    """Create sample privacy settings for testing."""
    return PrivacySettings(
        user_id="test-user-123",
        privacy_mode=PrivacyMode.FULL_MEMORY,
        data_retention_policy=DataRetentionPolicy.DAYS_90
    )


class TestMemoryAPI:
    """Test cases for memory service API endpoints."""
    
    @patch('src.memory.api.router.get_memory_service')
    def test_store_conversation_success(self, mock_get_service, sample_conversation):
        """Test successful conversation storage."""
        # Mock the memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.store_conversation = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Prepare request data
        request_data = {
            "conversation": sample_conversation.model_dump(mode='json')
        }
        
        # Make the request
        response = client.post("/memory/conversations", json=request_data)
        
        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Conversation stored successfully"
        assert data["conversation_id"] == sample_conversation.id
        
        # Verify service was called
        mock_service.store_conversation.assert_called_once()
    
    @patch('src.memory.api.router.get_memory_service')
    def test_retrieve_context_success(self, mock_get_service, sample_context):
        """Test successful context retrieval."""
        # Mock the memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.retrieve_context = AsyncMock(return_value=sample_context)
        mock_get_service.return_value = mock_service
        
        # Make the request
        response = client.get("/memory/context/test-user-123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Context retrieved successfully"
        assert data["context"]["user_id"] == "test-user-123"
        
        # Verify service was called
        mock_service.retrieve_context.assert_called_once_with("test-user-123", None)
    
    @patch('src.memory.api.router.get_memory_service')
    def test_search_history_success(self, mock_get_service, sample_search_results):
        """Test successful history search."""
        # Mock the memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.search_history = AsyncMock(return_value=sample_search_results)
        mock_get_service.return_value = mock_service
        
        # Prepare request data
        request_data = {
            "user_id": "test-user-123",
            "keywords": ["hello"],
            "limit": 20,
            "offset": 0
        }
        
        # Make the request
        response = client.post("/memory/search", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Search completed successfully"
        assert len(data["results"]) == 1
        assert data["total_count"] == 1
        assert data["has_more"] is False
        
        # Verify service was called
        mock_service.search_history.assert_called_once()
    
    @patch('src.memory.api.router.get_memory_service')
    def test_health_check_success(self, mock_get_service):
        """Test successful health check."""
        # Mock health status
        health_status = {
            "memory_service": "healthy",
            "components": {
                "storage": "healthy",
                "context_manager": "healthy"
            },
            "initialized": True
        }
        
        # Mock the memory service
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.health_check = AsyncMock(return_value=health_status)
        mock_get_service.return_value = mock_service
        
        # Make the request
        response = client.get("/memory/health")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["initialized"] is True
        assert "storage" in data["components"]
        
        # Verify service was called
        mock_service.health_check.assert_called_once()
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "/memory" in data["endpoints"]["memory"]
    
    def test_basic_chat_endpoint(self):
        """Test the basic chat endpoint still works."""
        # Mock the external API call
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "Hello there!"}
            mock_post.return_value = mock_response
            
            response = client.post("/chat", json={"user_input": "Hello"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == "Hello there!"