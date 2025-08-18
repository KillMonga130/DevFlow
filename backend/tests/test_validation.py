"""
Tests for validation utilities.
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.memory.models import (
    Message, MessageRole, Conversation, ConversationContext,
    UserPreferences, SearchQuery, PrivacySettings, DateRange,
    TopicInterest, ResponseStyle, CommunicationPreferences
)
from src.memory.utils.validation import (
    validate_user_id, validate_message, validate_conversation_data,
    validate_conversation_context, validate_user_preferences,
    validate_search_query, validate_privacy_settings,
    ValidationError, validate_and_raise
)


class TestUserIdValidation:
    """Test user ID validation."""
    
    def test_valid_user_ids(self):
        """Test valid user ID formats."""
        valid_ids = [
            "user123",
            "user-123",
            "user_123",
            "USER123",
            "a",
            "123",
            "user-test_123"
        ]
        
        for user_id in valid_ids:
            assert validate_user_id(user_id), f"Should be valid: {user_id}"
    
    def test_invalid_user_ids(self):
        """Test invalid user ID formats."""
        invalid_ids = [
            "",
            None,
            123,
            "user@123",
            "user 123",
            "user.123",
            "user#123",
            "a" * 256  # Too long
        ]
        
        for user_id in invalid_ids:
            assert not validate_user_id(user_id), f"Should be invalid: {user_id}"


class TestMessageValidation:
    """Test message validation."""
    
    def test_valid_message(self):
        """Test validation of a valid message."""
        message = Message(
            id="msg-123",
            role=MessageRole.USER,
            content="Hello, world!",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = validate_message(message)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_message_missing_id(self):
        """Test message with missing ID."""
        message = Message(
            id="",
            role=MessageRole.USER,
            content="Hello, world!",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = validate_message(message)
        assert not result["valid"]
        assert any("ID is required" in error for error in result["errors"])
    
    def test_message_long_id(self):
        """Test message with too long ID."""
        message = Message(
            id="a" * 256,
            role=MessageRole.USER,
            content="Hello, world!",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = validate_message(message)
        assert not result["valid"]
        assert any("too long" in error for error in result["errors"])
    
    def test_message_empty_content(self):
        """Test message with empty content - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            Message(
                id="msg-123",
                role=MessageRole.USER,
                content="",
                timestamp=datetime.now(timezone.utc)
            )
    
    def test_message_future_timestamp(self):
        """Test message with future timestamp."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        message = Message(
            id="msg-123",
            role=MessageRole.USER,
            content="Hello, world!",
            timestamp=future_time
        )
        
        result = validate_message(message)
        assert result["valid"]  # Should be valid but with warning
        assert any("future" in warning for warning in result["warnings"])


class TestConversationValidation:
    """Test conversation validation."""
    
    def test_valid_conversation(self):
        """Test validation of a valid conversation."""
        message = Message(
            id="msg-1",
            role=MessageRole.USER,
            content="Test message",
            timestamp=datetime.now(timezone.utc)
        )
        
        conversation = Conversation(
            id="conv-123",
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            messages=[message]
        )
        
        result = validate_conversation_data(conversation)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_conversation_invalid_user_id(self):
        """Test conversation with invalid user ID."""
        message = Message(
            id="msg-1",
            role=MessageRole.USER,
            content="Test message",
            timestamp=datetime.now(timezone.utc)
        )
        
        conversation = Conversation(
            id="conv-123",
            user_id="invalid@user",
            timestamp=datetime.now(timezone.utc),
            messages=[message]
        )
        
        result = validate_conversation_data(conversation)
        assert not result["valid"]
        assert any("Invalid user ID" in error for error in result["errors"])
    
    def test_conversation_no_messages(self):
        """Test conversation with no messages."""
        conversation = Conversation(
            id="conv-123",
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            messages=[]
        )
        
        result = validate_conversation_data(conversation)
        assert result["valid"]  # Valid but with warning
        assert any("no messages" in warning for warning in result["warnings"])


class TestConversationContextValidation:
    """Test conversation context validation."""
    
    def test_valid_context(self):
        """Test validation of valid conversation context."""
        message = Message(
            id="msg-1",
            role=MessageRole.USER,
            content="Test message",
            timestamp=datetime.now(timezone.utc)
        )
        
        context = ConversationContext(
            user_id="user-123",
            recent_messages=[message],
            context_summary="Test summary"
        )
        
        result = validate_conversation_context(context)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_context_invalid_user_id(self):
        """Test context with invalid user ID."""
        context = ConversationContext(
            user_id="invalid@user",
            recent_messages=[],
            context_summary=""
        )
        
        result = validate_conversation_context(context)
        assert not result["valid"]
        assert any("Invalid user ID" in error for error in result["errors"])
    
    def test_context_many_messages_warning(self):
        """Test context with many messages generates warning."""
        messages = [
            Message(
                id=f"msg-{i}",
                role=MessageRole.USER,
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc)
            )
            for i in range(101)
        ]
        
        context = ConversationContext(
            user_id="user-123",
            recent_messages=messages
        )
        
        result = validate_conversation_context(context)
        assert result["valid"]
        assert any("many recent messages" in warning for warning in result["warnings"])


class TestUserPreferencesValidation:
    """Test user preferences validation."""
    
    def test_valid_preferences(self):
        """Test validation of valid user preferences."""
        preferences = UserPreferences(
            user_id="user-123",
            topic_interests=[
                TopicInterest(topic="python", interest_level=0.8, frequency_mentioned=5),
                TopicInterest(topic="ai", interest_level=0.9, frequency_mentioned=10)
            ]
        )
        
        result = validate_user_preferences(preferences)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_preferences_invalid_interest_level(self):
        """Test preferences with invalid interest level - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            TopicInterest(topic="python", interest_level=1.5, frequency_mentioned=5)
    
    def test_preferences_negative_frequency(self):
        """Test preferences with negative frequency - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            TopicInterest(topic="python", interest_level=0.8, frequency_mentioned=-1)
    
    def test_preferences_duplicate_topics(self):
        """Test preferences with duplicate topics - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            UserPreferences(
                user_id="user-123",
                topic_interests=[
                    TopicInterest(topic="python", interest_level=0.8, frequency_mentioned=5),
                    TopicInterest(topic="Python", interest_level=0.9, frequency_mentioned=3)
                ]
            )


class TestSearchQueryValidation:
    """Test search query validation."""
    
    def test_valid_search_query(self):
        """Test validation of valid search query."""
        query = SearchQuery(
            user_id="user-123",
            keywords=["python", "programming"],
            limit=10,
            offset=0
        )
        
        result = validate_search_query(query)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_search_query_invalid_limit(self):
        """Test search query with invalid limit - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            SearchQuery(
                user_id="user-123",
                limit=0
            )
    
    def test_search_query_negative_offset(self):
        """Test search query with negative offset - should fail at Pydantic level."""
        with pytest.raises(Exception):  # Pydantic validation error
            SearchQuery(
                user_id="user-123",
                offset=-1
            )
    
    def test_search_query_invalid_date_range(self):
        """Test search query with invalid date range."""
        start_date = datetime.now(timezone.utc)
        end_date = start_date - timedelta(days=1)
        
        query = SearchQuery(
            user_id="user-123",
            date_range=DateRange(start_date=start_date, end_date=end_date)
        )
        
        result = validate_search_query(query)
        assert not result["valid"]
        assert any("start must be before end" in error for error in result["errors"])


class TestPrivacySettingsValidation:
    """Test privacy settings validation."""
    
    def test_valid_privacy_settings(self):
        """Test validation of valid privacy settings."""
        settings = PrivacySettings(
            user_id="user-123",
            allow_preference_learning=True,
            allow_search_indexing=True
        )
        
        result = validate_privacy_settings(settings)
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_privacy_settings_conflicting_preferences(self):
        """Test privacy settings with conflicting preferences."""
        settings = PrivacySettings(
            user_id="user-123",
            privacy_mode="no_memory",
            allow_preference_learning=True
        )
        
        result = validate_privacy_settings(settings)
        assert result["valid"]  # Valid but with warning
        assert any("memory is disabled" in warning for warning in result["warnings"])


class TestValidationError:
    """Test ValidationError exception."""
    
    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        
        error = ValidationError("Test validation failed", errors, warnings)
        
        assert str(error) == "Test validation failed"
        assert error.errors == errors
        assert error.warnings == warnings
    
    def test_validate_and_raise_success(self):
        """Test validate_and_raise with valid result."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Should not raise
        validate_and_raise(result, "Test context")
    
    def test_validate_and_raise_failure(self):
        """Test validate_and_raise with invalid result."""
        result = {
            "valid": False, 
            "errors": ["Test error"], 
            "warnings": ["Test warning"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_and_raise(result, "Test context")
        
        assert "Test context failed" in str(exc_info.value)
        assert exc_info.value.errors == ["Test error"]
        assert exc_info.value.warnings == ["Test warning"]


if __name__ == "__main__":
    pytest.main([__file__])