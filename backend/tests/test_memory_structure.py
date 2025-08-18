"""
Basic tests to verify the memory system structure is set up correctly.
"""

import pytest
from datetime import datetime
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    UserPreferences, SearchQuery, PrivacySettings
)
from src.memory.services import MemoryService
from src.memory.config import get_memory_config


def test_message_creation():
    """Test that Message model can be created."""
    message = Message(
        id="test-id",
        role=MessageRole.USER,
        content="Hello, world!",
        timestamp=datetime.utcnow()
    )
    
    assert message.id == "test-id"
    assert message.role == MessageRole.USER
    assert message.content == "Hello, world!"
    assert isinstance(message.timestamp, datetime)


def test_conversation_creation():
    """Test that Conversation model can be created."""
    message = Message(
        id="msg-1",
        role=MessageRole.USER,
        content="Test message",
        timestamp=datetime.utcnow()
    )
    
    conversation = Conversation(
        id="conv-1",
        user_id="user-123",
        timestamp=datetime.utcnow(),
        messages=[message]
    )
    
    assert conversation.id == "conv-1"
    assert conversation.user_id == "user-123"
    assert len(conversation.messages) == 1
    assert conversation.messages[0].content == "Test message"


def test_conversation_context_creation():
    """Test that ConversationContext can be created."""
    context = ConversationContext(user_id="user-123")
    
    assert context.user_id == "user-123"
    assert len(context.recent_messages) == 0
    assert len(context.relevant_history) == 0
    assert context.context_summary == ""


def test_user_preferences_creation():
    """Test that UserPreferences can be created."""
    preferences = UserPreferences(user_id="user-123")
    
    assert preferences.user_id == "user-123"
    assert preferences.learning_enabled is True
    assert len(preferences.topic_interests) == 0


def test_search_query_creation():
    """Test that SearchQuery can be created."""
    query = SearchQuery(
        keywords=["test", "query"],
        user_id="user-123",
        limit=10
    )
    
    assert query.keywords == ["test", "query"]
    assert query.user_id == "user-123"
    assert query.limit == 10
    assert query.has_filters() is True


def test_privacy_settings_creation():
    """Test that PrivacySettings can be created."""
    settings = PrivacySettings(user_id="user-123")
    
    assert settings.user_id == "user-123"
    assert settings.is_memory_enabled() is True
    assert settings.allows_long_term_storage() is True


def test_memory_service_instantiation():
    """Test that MemoryService can be instantiated."""
    service = MemoryService()
    assert service is not None


def test_config_loading():
    """Test that configuration can be loaded."""
    config = get_memory_config()
    assert config is not None
    assert hasattr(config, 'max_context_messages')
    assert hasattr(config, 'context_retention_days')


if __name__ == "__main__":
    pytest.main([__file__])