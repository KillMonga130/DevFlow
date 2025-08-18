"""
Tests for conversation data models.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from src.memory.models.conversation import (
    Message, MessageRole, MessageMetadata,
    Conversation, ConversationMetadata
)


class TestMessageMetadata:
    """Test MessageMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating message metadata."""
        metadata = MessageMetadata(
            tokens=100,
            processing_time=0.5,
            model_used="gpt-4",
            confidence_score=0.95
        )
        
        assert metadata.tokens == 100
        assert metadata.processing_time == 0.5
        assert metadata.model_used == "gpt-4"
        assert metadata.confidence_score == 0.95
        assert isinstance(metadata.created_at, datetime)
    
    def test_metadata_validation(self):
        """Test metadata validation."""
        # Test negative tokens
        with pytest.raises(ValueError, match="Token count cannot be negative"):
            MessageMetadata(tokens=-1)
        
        # Test negative processing time
        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            MessageMetadata(processing_time=-1.0)
        
        # Test invalid confidence score
        with pytest.raises(ValueError, match="Confidence score must be between"):
            MessageMetadata(confidence_score=1.5)
    
    def test_metadata_serialization(self):
        """Test metadata serialization."""
        metadata = MessageMetadata(
            tokens=100,
            model_used="gpt-4",
            additional_data={"custom": "value"}
        )
        
        # Test to_dict
        data = metadata.to_dict()
        assert data["tokens"] == 100
        assert data["model_used"] == "gpt-4"
        assert data["additional_data"]["custom"] == "value"
        
        # Test from_dict
        restored = MessageMetadata.from_dict(data)
        assert restored.tokens == metadata.tokens
        assert restored.model_used == metadata.model_used
        assert restored.additional_data == metadata.additional_data


class TestMessage:
    """Test Message model."""
    
    def test_message_creation(self):
        """Test creating a message."""
        message = Message(
            role=MessageRole.USER,
            content="Hello, world!"
        )
        
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.id, str)
        assert isinstance(message.timestamp, datetime)
        assert isinstance(message.metadata, MessageMetadata)
    
    def test_message_validation(self):
        """Test message validation."""
        # Test empty content
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            Message(role=MessageRole.USER, content="")
        
        # Test content too long
        long_content = "x" * 50001
        with pytest.raises(ValueError, match="Message content too long"):
            Message(role=MessageRole.USER, content=long_content)
    
    def test_message_serialization(self):
        """Test message serialization."""
        message = Message(
            role=MessageRole.USER,
            content="Test message"
        )
        
        # Test to_dict
        data = message.to_dict()
        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert "timestamp" in data
        assert "metadata" in data
        
        # Test from_dict
        restored = Message.from_dict(data)
        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.id == message.id
    
    def test_message_json_serialization(self):
        """Test JSON serialization."""
        message = Message(
            role=MessageRole.ASSISTANT,
            content="Test response"
        )
        
        # Test to_json
        json_str = message.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        restored = Message.from_json(json_str)
        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.id == message.id
    
    def test_message_metadata_update(self):
        """Test updating message metadata."""
        message = Message(
            role=MessageRole.USER,
            content="Test message"
        )
        
        # Update metadata
        message.update_metadata(
            tokens=50,
            model_used="gpt-3.5",
            custom_field="custom_value"
        )
        
        assert message.metadata.tokens == 50
        assert message.metadata.model_used == "gpt-3.5"
        assert message.metadata.additional_data["custom_field"] == "custom_value"
        assert message.metadata.updated_at is not None


class TestConversationMetadata:
    """Test ConversationMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating conversation metadata."""
        metadata = ConversationMetadata(
            total_messages=5,
            total_tokens=1000,
            topics=["python", "ai"],
            sentiment="positive"
        )
        
        assert metadata.total_messages == 5
        assert metadata.total_tokens == 1000
        assert metadata.topics == ["python", "ai"]
        assert metadata.sentiment == "positive"
    
    def test_metadata_validation(self):
        """Test metadata validation."""
        # Test negative message count
        with pytest.raises(ValueError, match="Total messages cannot be negative"):
            ConversationMetadata(total_messages=-1)
        
        # Test negative tokens
        with pytest.raises(ValueError, match="Total tokens cannot be negative"):
            ConversationMetadata(total_tokens=-1)
        
        # Test negative duration
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            ConversationMetadata(duration_seconds=-1.0)
    
    def test_metadata_update_stats(self):
        """Test updating message statistics."""
        metadata = ConversationMetadata()
        timestamp = datetime.now(timezone.utc)
        
        metadata.update_message_stats(10, timestamp)
        
        assert metadata.total_messages == 10
        assert metadata.last_message_at == timestamp
        assert metadata.updated_at is not None


class TestConversation:
    """Test Conversation model."""
    
    def test_conversation_creation(self):
        """Test creating a conversation."""
        conversation = Conversation(
            user_id="user-123"
        )
        
        assert conversation.user_id == "user-123"
        assert isinstance(conversation.id, str)
        assert isinstance(conversation.timestamp, datetime)
        assert len(conversation.messages) == 0
        assert isinstance(conversation.metadata, ConversationMetadata)
    
    def test_conversation_validation(self):
        """Test conversation validation."""
        # Test empty user ID
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            Conversation(user_id="")
        
        # Test user ID too long
        long_user_id = "x" * 256
        with pytest.raises(ValueError, match="User ID too long"):
            Conversation(user_id=long_user_id)
        
        # Test summary too long
        long_summary = "x" * 5001
        with pytest.raises(ValueError, match="Summary too long"):
            Conversation(user_id="user-123", summary=long_summary)
    
    def test_add_message(self):
        """Test adding messages to conversation."""
        conversation = Conversation(user_id="user-123")
        
        message1 = Message(role=MessageRole.USER, content="Hello")
        message2 = Message(role=MessageRole.ASSISTANT, content="Hi there!")
        
        conversation.add_message(message1)
        assert len(conversation.messages) == 1
        assert conversation.metadata.total_messages == 1
        
        conversation.add_message(message2)
        assert len(conversation.messages) == 2
        assert conversation.metadata.total_messages == 2
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages at once."""
        conversation = Conversation(user_id="user-123")
        
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi!"),
            Message(role=MessageRole.USER, content="How are you?")
        ]
        
        conversation.add_messages(messages)
        assert len(conversation.messages) == 3
        assert conversation.metadata.total_messages == 3
    
    def test_get_latest_messages(self):
        """Test getting latest messages."""
        conversation = Conversation(user_id="user-123")
        
        # Add 5 messages
        for i in range(5):
            message = Message(role=MessageRole.USER, content=f"Message {i}")
            conversation.add_message(message)
        
        # Get latest 3 messages
        latest = conversation.get_latest_messages(3)
        assert len(latest) == 3
        assert latest[0].content == "Message 2"
        assert latest[2].content == "Message 4"
        
        # Get more messages than available
        all_messages = conversation.get_latest_messages(10)
        assert len(all_messages) == 5
    
    def test_get_messages_by_role(self):
        """Test getting messages by role."""
        conversation = Conversation(user_id="user-123")
        
        conversation.add_message(Message(role=MessageRole.USER, content="User 1"))
        conversation.add_message(Message(role=MessageRole.ASSISTANT, content="Assistant 1"))
        conversation.add_message(Message(role=MessageRole.USER, content="User 2"))
        
        user_messages = conversation.get_messages_by_role(MessageRole.USER)
        assert len(user_messages) == 2
        assert all(msg.role == MessageRole.USER for msg in user_messages)
        
        assistant_messages = conversation.get_messages_by_role(MessageRole.ASSISTANT)
        assert len(assistant_messages) == 1
        assert assistant_messages[0].role == MessageRole.ASSISTANT
    
    def test_get_messages_in_range(self):
        """Test getting messages in time range."""
        conversation = Conversation(user_id="user-123")
        
        base_time = datetime.now(timezone.utc)
        
        # Add messages with different timestamps
        for i in range(3):
            timestamp = base_time + timedelta(minutes=i)
            message = Message(
                role=MessageRole.USER, 
                content=f"Message {i}",
                timestamp=timestamp
            )
            conversation.add_message(message)
        
        # Get messages in range
        start_time = base_time + timedelta(minutes=0.5)
        end_time = base_time + timedelta(minutes=1.5)
        
        messages_in_range = conversation.get_messages_in_range(start_time, end_time)
        assert len(messages_in_range) == 1
        assert messages_in_range[0].content == "Message 1"
    
    def test_calculate_duration(self):
        """Test calculating conversation duration."""
        conversation = Conversation(user_id="user-123")
        
        # No messages - should return None
        assert conversation.calculate_duration() is None
        
        # Single message - should return None
        conversation.add_message(Message(role=MessageRole.USER, content="Hello"))
        assert conversation.calculate_duration() is None
        
        # Multiple messages
        base_time = datetime.now(timezone.utc)
        message1 = Message(
            role=MessageRole.USER, 
            content="First",
            timestamp=base_time
        )
        message2 = Message(
            role=MessageRole.ASSISTANT, 
            content="Second",
            timestamp=base_time + timedelta(minutes=5)
        )
        
        conversation = Conversation(user_id="user-123")
        conversation.add_message(message1)
        conversation.add_message(message2)
        
        duration = conversation.calculate_duration()
        assert duration == 300.0  # 5 minutes in seconds
        assert conversation.metadata.duration_seconds == 300.0
    
    def test_conversation_serialization(self):
        """Test conversation serialization."""
        conversation = Conversation(
            user_id="user-123",
            tags=["test", "demo"]
        )
        
        conversation.add_message(Message(role=MessageRole.USER, content="Hello"))
        conversation.add_message(Message(role=MessageRole.ASSISTANT, content="Hi!"))
        
        # Test to_dict
        data = conversation.to_dict()
        assert data["user_id"] == "user-123"
        assert data["tags"] == ["test", "demo"]
        assert len(data["messages"]) == 2
        
        # Test from_dict
        restored = Conversation.from_dict(data)
        assert restored.user_id == conversation.user_id
        assert restored.tags == conversation.tags
        assert len(restored.messages) == len(conversation.messages)
        assert restored.messages[0].content == conversation.messages[0].content
    
    def test_conversation_json_serialization(self):
        """Test JSON serialization."""
        conversation = Conversation(user_id="user-123")
        conversation.add_message(Message(role=MessageRole.USER, content="Test"))
        
        # Test to_json
        json_str = conversation.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        restored = Conversation.from_json(json_str)
        assert restored.user_id == conversation.user_id
        assert len(restored.messages) == len(conversation.messages)
        assert restored.messages[0].content == conversation.messages[0].content
    
    def test_conversation_clone(self):
        """Test cloning a conversation."""
        original = Conversation(user_id="user-123")
        original.add_message(Message(role=MessageRole.USER, content="Original"))
        
        cloned = original.clone()
        
        # Should be equal but different objects
        assert cloned.user_id == original.user_id
        assert len(cloned.messages) == len(original.messages)
        assert cloned.messages[0].content == original.messages[0].content
        assert cloned is not original
        assert cloned.id != original.id  # Should have different IDs
    
    def test_conversation_merge(self):
        """Test merging conversations."""
        base_time = datetime.now(timezone.utc)
        
        # Create first conversation
        conv1 = Conversation(user_id="user-123", timestamp=base_time)
        conv1.add_message(Message(
            role=MessageRole.USER, 
            content="First message",
            timestamp=base_time
        ))
        conv1.tags = ["tag1"]
        
        # Create second conversation
        conv2 = Conversation(user_id="user-123", timestamp=base_time + timedelta(minutes=5))
        conv2.add_message(Message(
            role=MessageRole.USER, 
            content="Second message",
            timestamp=base_time + timedelta(minutes=5)
        ))
        conv2.tags = ["tag2"]
        
        # Merge conversations
        merged = conv1.merge_with(conv2)
        
        assert merged.user_id == "user-123"
        assert len(merged.messages) == 2
        assert merged.messages[0].content == "First message"  # Should be sorted by timestamp
        assert merged.messages[1].content == "Second message"
        assert set(merged.tags) == {"tag1", "tag2"}
        assert merged.timestamp == base_time  # Should use earliest timestamp
    
    def test_conversation_merge_different_users(self):
        """Test merging conversations from different users should fail."""
        conv1 = Conversation(user_id="user-123")
        conv2 = Conversation(user_id="user-456")
        
        with pytest.raises(ValueError, match="Cannot merge conversations from different users"):
            conv1.merge_with(conv2)


if __name__ == "__main__":
    pytest.main([__file__])