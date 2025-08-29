"""
Unit tests for common data models.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from src.memory.models.common import (
    FeedbackType, MessageExchange, UserFeedback
)
from src.memory.models.conversation import Message, MessageRole


class TestFeedbackType:
    """Test cases for FeedbackType enum."""
    
    def test_feedback_type_values(self):
        """Test that FeedbackType has expected values."""
        assert FeedbackType.POSITIVE == "positive"
        assert FeedbackType.NEGATIVE == "negative"
        assert FeedbackType.CORRECTION == "correction"
        assert FeedbackType.PREFERENCE == "preference"
    
    def test_feedback_type_membership(self):
        """Test membership checks for FeedbackType."""
        assert "positive" in FeedbackType
        assert "negative" in FeedbackType
        assert "correction" in FeedbackType
        assert "preference" in FeedbackType
        assert "invalid" not in FeedbackType
    
    def test_feedback_type_iteration(self):
        """Test iteration over FeedbackType values."""
        expected_values = {"positive", "negative", "correction", "preference"}
        actual_values = {feedback_type.value for feedback_type in FeedbackType}
        assert actual_values == expected_values


class TestMessageExchange:
    """Test cases for MessageExchange model."""
    
    @pytest.fixture
    def sample_user_message(self):
        """Create a sample user message."""
        return Message(
            id="user_msg_1",
            role=MessageRole.USER,
            content="What's the weather like?",
            timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
    
    @pytest.fixture
    def sample_assistant_message(self):
        """Create a sample assistant message."""
        return Message(
            id="assistant_msg_1",
            role=MessageRole.ASSISTANT,
            content="The weather is sunny today.",
            timestamp=datetime(2023, 1, 1, 10, 0, 5, tzinfo=timezone.utc)  # 5 seconds later
        )
    
    def test_message_exchange_creation(self, sample_user_message, sample_assistant_message):
        """Test creating a basic message exchange."""
        exchange = MessageExchange(
            user_message=sample_user_message,
            assistant_message=sample_assistant_message
        )
        
        assert exchange.user_message == sample_user_message
        assert exchange.assistant_message == sample_assistant_message
        assert isinstance(exchange.exchange_timestamp, datetime)
        assert exchange.context_used is None
        assert exchange.preferences_applied is None
    
    def test_message_exchange_with_context(self, sample_user_message, sample_assistant_message):
        """Test creating a message exchange with context."""
        context = "Previous conversation about weather preferences"
        preferences = {"response_style": "casual", "include_details": True}
        
        exchange = MessageExchange(
            user_message=sample_user_message,
            assistant_message=sample_assistant_message,
            context_used=context,
            preferences_applied=preferences
        )
        
        assert exchange.context_used == context
        assert exchange.preferences_applied == preferences
    
    def test_message_exchange_custom_timestamp(self, sample_user_message, sample_assistant_message):
        """Test creating a message exchange with custom timestamp."""
        custom_timestamp = datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        
        exchange = MessageExchange(
            user_message=sample_user_message,
            assistant_message=sample_assistant_message,
            exchange_timestamp=custom_timestamp
        )
        
        assert exchange.exchange_timestamp == custom_timestamp
    
    def test_get_exchange_duration(self, sample_user_message, sample_assistant_message):
        """Test calculating exchange duration."""
        exchange = MessageExchange(
            user_message=sample_user_message,
            assistant_message=sample_assistant_message
        )
        
        duration = exchange.get_exchange_duration()
        
        # Assistant message is 5 seconds after user message
        assert duration == 5.0
    
    def test_get_exchange_duration_negative(self):
        """Test exchange duration when assistant message is before user message."""
        user_message = Message(
            id="user_msg",
            role=MessageRole.USER,
            content="Hello",
            timestamp=datetime(2023, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
        )
        
        assistant_message = Message(
            id="assistant_msg",
            role=MessageRole.ASSISTANT,
            content="Hi",
            timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)  # 5 seconds before
        )
        
        exchange = MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message
        )
        
        duration = exchange.get_exchange_duration()
        assert duration == -5.0  # Negative duration
    
    def test_message_exchange_serialization(self, sample_user_message, sample_assistant_message):
        """Test serialization of message exchange."""
        exchange = MessageExchange(
            user_message=sample_user_message,
            assistant_message=sample_assistant_message,
            context_used="test context"
        )
        
        data = exchange.model_dump()
        
        assert isinstance(data, dict)
        assert "user_message" in data
        assert "assistant_message" in data
        assert "exchange_timestamp" in data
        assert "context_used" in data
        assert data["context_used"] == "test context"
    
    def test_message_exchange_validation_missing_fields(self):
        """Test validation when required fields are missing."""
        with pytest.raises(ValidationError):
            MessageExchange()
        
        with pytest.raises(ValidationError):
            MessageExchange(user_message=None, assistant_message=None)


class TestUserFeedback:
    """Test cases for UserFeedback model."""
    
    def test_user_feedback_creation_minimal(self):
        """Test creating user feedback with minimal required fields."""
        feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.POSITIVE
        )
        
        assert feedback.user_id == "user123"
        assert feedback.message_id == "msg456"
        assert feedback.feedback_type == FeedbackType.POSITIVE
        assert feedback.feedback_text is None
        assert feedback.rating is None
        assert isinstance(feedback.timestamp, datetime)
        assert feedback.context is None
    
    def test_user_feedback_creation_full(self):
        """Test creating user feedback with all fields."""
        custom_timestamp = datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        context = {"conversation_id": "conv123", "topic": "weather"}
        
        feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.CORRECTION,
            feedback_text="The response should mention temperature",
            rating=3,
            timestamp=custom_timestamp,
            context=context
        )
        
        assert feedback.user_id == "user123"
        assert feedback.message_id == "msg456"
        assert feedback.feedback_type == FeedbackType.CORRECTION
        assert feedback.feedback_text == "The response should mention temperature"
        assert feedback.rating == 3
        assert feedback.timestamp == custom_timestamp
        assert feedback.context == context
    
    def test_user_feedback_rating_validation(self):
        """Test rating field validation."""
        # Valid ratings (1-5)
        for rating in [1, 2, 3, 4, 5]:
            feedback = UserFeedback(
                user_id="user123",
                message_id="msg456",
                feedback_type=FeedbackType.POSITIVE,
                rating=rating
            )
            assert feedback.rating == rating
        
        # Invalid ratings
        invalid_ratings = [0, 6, -1, 10]
        for rating in invalid_ratings:
            with pytest.raises(ValidationError):
                UserFeedback(
                    user_id="user123",
                    message_id="msg456",
                    feedback_type=FeedbackType.POSITIVE,
                    rating=rating
                )
    
    def test_user_feedback_is_positive_by_type(self):
        """Test is_positive method based on feedback type."""
        positive_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.POSITIVE
        )
        
        negative_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.NEGATIVE
        )
        
        assert positive_feedback.is_positive() is True
        assert negative_feedback.is_positive() is False
    
    def test_user_feedback_is_positive_by_rating(self):
        """Test is_positive method based on rating."""
        # High rating (4-5) should be positive
        high_rating_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.NEGATIVE,  # Type is negative but rating is high
            rating=4
        )
        
        # Low rating (1-3) should not be positive based on rating alone
        low_rating_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.NEGATIVE,
            rating=2
        )
        
        assert high_rating_feedback.is_positive() is True  # High rating overrides type
        assert low_rating_feedback.is_positive() is False
    
    def test_user_feedback_is_positive_no_rating(self):
        """Test is_positive method when no rating is provided."""
        correction_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.CORRECTION
        )
        
        preference_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.PREFERENCE
        )
        
        assert correction_feedback.is_positive() is False
        assert preference_feedback.is_positive() is False
    
    def test_user_feedback_is_correction(self):
        """Test is_correction method."""
        correction_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.CORRECTION
        )
        
        positive_feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.POSITIVE
        )
        
        assert correction_feedback.is_correction() is True
        assert positive_feedback.is_correction() is False
    
    def test_user_feedback_validation_missing_fields(self):
        """Test validation when required fields are missing."""
        with pytest.raises(ValidationError):
            UserFeedback()
        
        with pytest.raises(ValidationError):
            UserFeedback(user_id="user123")
        
        with pytest.raises(ValidationError):
            UserFeedback(user_id="user123", message_id="msg456")
    
    def test_user_feedback_validation_empty_strings(self):
        """Test validation with empty string values."""
        with pytest.raises(ValidationError):
            UserFeedback(
                user_id="",
                message_id="msg456",
                feedback_type=FeedbackType.POSITIVE
            )
        
        with pytest.raises(ValidationError):
            UserFeedback(
                user_id="user123",
                message_id="",
                feedback_type=FeedbackType.POSITIVE
            )
    
    def test_user_feedback_serialization(self):
        """Test serialization of user feedback."""
        feedback = UserFeedback(
            user_id="user123",
            message_id="msg456",
            feedback_type=FeedbackType.CORRECTION,
            feedback_text="Please be more specific",
            rating=3,
            context={"topic": "weather"}
        )
        
        data = feedback.model_dump()
        
        assert isinstance(data, dict)
        assert data["user_id"] == "user123"
        assert data["message_id"] == "msg456"
        assert data["feedback_type"] == "correction"
        assert data["feedback_text"] == "Please be more specific"
        assert data["rating"] == 3
        assert data["context"] == {"topic": "weather"}
        assert "timestamp" in data
    
    def test_user_feedback_deserialization(self):
        """Test creating user feedback from dictionary."""
        data = {
            "user_id": "user123",
            "message_id": "msg456",
            "feedback_type": "positive",
            "feedback_text": "Great response!",
            "rating": 5,
            "timestamp": "2023-06-15T14:30:00Z",
            "context": {"helpful": True}
        }
        
        feedback = UserFeedback(**data)
        
        assert feedback.user_id == "user123"
        assert feedback.message_id == "msg456"
        assert feedback.feedback_type == FeedbackType.POSITIVE
        assert feedback.feedback_text == "Great response!"
        assert feedback.rating == 5
        assert feedback.context == {"helpful": True}


class TestModelIntegration:
    """Integration tests for common models."""
    
    def test_message_exchange_with_feedback(self):
        """Test using message exchange with user feedback."""
        user_message = Message(
            id="user_msg_1",
            role=MessageRole.USER,
            content="Tell me about Python",
            timestamp=datetime.now(timezone.utc)
        )
        
        assistant_message = Message(
            id="assistant_msg_1",
            role=MessageRole.ASSISTANT,
            content="Python is a programming language",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=2)
        )
        
        exchange = MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message
        )
        
        feedback = UserFeedback(
            user_id="user123",
            message_id=assistant_message.id,
            feedback_type=FeedbackType.POSITIVE,
            rating=5
        )
        
        # Should be able to use both models together
        assert exchange.assistant_message.id == feedback.message_id
        assert feedback.is_positive() is True
        assert exchange.get_exchange_duration() == 2.0
    
    def test_feedback_types_in_context(self):
        """Test using different feedback types in various contexts."""
        message_id = "msg123"
        user_id = "user456"
        
        # Create different types of feedback
        feedbacks = [
            UserFeedback(
                user_id=user_id,
                message_id=message_id,
                feedback_type=FeedbackType.POSITIVE,
                rating=5
            ),
            UserFeedback(
                user_id=user_id,
                message_id=message_id,
                feedback_type=FeedbackType.NEGATIVE,
                rating=2
            ),
            UserFeedback(
                user_id=user_id,
                message_id=message_id,
                feedback_type=FeedbackType.CORRECTION,
                feedback_text="Should include more details"
            ),
            UserFeedback(
                user_id=user_id,
                message_id=message_id,
                feedback_type=FeedbackType.PREFERENCE,
                feedback_text="I prefer shorter responses"
            )
        ]
        
        # Test feedback analysis
        positive_count = sum(1 for f in feedbacks if f.is_positive())
        correction_count = sum(1 for f in feedbacks if f.is_correction())
        
        assert positive_count == 1  # Only the first one is positive
        assert correction_count == 1  # Only the correction type
    
    def test_model_validation_consistency(self):
        """Test that model validation is consistent across different scenarios."""
        # Test that all models handle timezone-aware datetimes
        timestamp = datetime.now(timezone.utc)
        
        user_message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="Test",
            timestamp=timestamp
        )
        
        assistant_message = Message(
            id="msg2",
            role=MessageRole.ASSISTANT,
            content="Response",
            timestamp=timestamp + timedelta(seconds=1)
        )
        
        exchange = MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message,
            exchange_timestamp=timestamp
        )
        
        feedback = UserFeedback(
            user_id="user123",
            message_id="msg2",
            feedback_type=FeedbackType.POSITIVE,
            timestamp=timestamp + timedelta(seconds=2)
        )
        
        # All timestamps should be timezone-aware
        assert exchange.user_message.timestamp.tzinfo is not None
        assert exchange.assistant_message.timestamp.tzinfo is not None
        assert exchange.exchange_timestamp.tzinfo is not None
        assert feedback.timestamp.tzinfo is not None


if __name__ == "__main__":
    pytest.main([__file__])