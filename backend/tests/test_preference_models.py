"""
Unit tests for user preference data models.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from src.memory.models.preferences import (
    UserPreferences, ResponseStyle, TopicInterest, CommunicationPreferences,
    ResponseStyleType, CommunicationTone
)


class TestResponseStyle:
    """Test ResponseStyle class."""
    
    def test_create_default_response_style(self):
        """Test creating response style with default values."""
        style = ResponseStyle()
        
        assert style.style_type == ResponseStyleType.CONVERSATIONAL
        assert style.tone == CommunicationTone.HELPFUL
        assert style.preferred_length is None
        assert style.include_examples is True
        assert style.include_explanations is True
        assert style.confidence == 0.0
        assert isinstance(style.created_at, datetime)
        assert style.updated_at is None
    
    def test_create_response_style_with_values(self):
        """Test creating response style with specific values."""
        style = ResponseStyle(
            style_type=ResponseStyleType.TECHNICAL,
            tone=CommunicationTone.PROFESSIONAL,
            preferred_length="short",
            include_examples=False,
            confidence=0.8
        )
        
        assert style.style_type == ResponseStyleType.TECHNICAL
        assert style.tone == CommunicationTone.PROFESSIONAL
        assert style.preferred_length == "short"
        assert style.include_examples is False
        assert style.confidence == 0.8
    
    def test_response_style_validation(self):
        """Test response style validation."""
        # Test invalid preferred length
        with pytest.raises(ValueError, match='Preferred length must be'):
            ResponseStyle(preferred_length="invalid")
        
        # Test invalid confidence
        with pytest.raises(ValueError, match='Confidence must be between 0.0 and 1.0'):
            ResponseStyle(confidence=1.5)
        
        with pytest.raises(ValueError, match='Confidence must be between 0.0 and 1.0'):
            ResponseStyle(confidence=-0.1)
    
    def test_response_style_serialization(self):
        """Test response style serialization."""
        style = ResponseStyle(
            style_type=ResponseStyleType.DETAILED,
            tone=CommunicationTone.FRIENDLY,
            preferred_length="medium",
            confidence=0.7
        )
        
        # Test to_dict
        data = style.to_dict()
        assert data["style_type"] == "detailed"
        assert data["tone"] == "friendly"
        assert data["preferred_length"] == "medium"
        assert data["confidence"] == 0.7
        
        # Test from_dict
        restored = ResponseStyle.from_dict(data)
        assert restored.style_type == style.style_type
        assert restored.tone == style.tone
        assert restored.preferred_length == style.preferred_length
        assert restored.confidence == style.confidence
    
    def test_update_confidence(self):
        """Test updating confidence level."""
        style = ResponseStyle()
        
        style.update_confidence(0.9)
        assert style.confidence == 0.9
        assert style.updated_at is not None
        
        # Test bounds checking
        style.update_confidence(1.5)
        assert style.confidence == 1.0
        
        style.update_confidence(-0.5)
        assert style.confidence == 0.0


class TestTopicInterest:
    """Test TopicInterest class."""
    
    def test_create_topic_interest(self):
        """Test creating topic interest."""
        interest = TopicInterest(
            topic="Python Programming",
            interest_level=0.8
        )
        
        assert interest.topic == "Python Programming"
        assert interest.interest_level == 0.8
        assert interest.frequency_mentioned == 0
        assert interest.last_mentioned is None
        assert interest.context_keywords == []
        assert isinstance(interest.created_at, datetime)
        assert interest.updated_at is None
    
    def test_topic_interest_validation(self):
        """Test topic interest validation."""
        # Test empty topic
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            TopicInterest(topic="", interest_level=0.5)
        
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            TopicInterest(topic="   ", interest_level=0.5)
        
        # Test topic too long
        long_topic = "x" * 201
        with pytest.raises(ValueError, match="Topic name too long"):
            TopicInterest(topic=long_topic, interest_level=0.5)
        
        # Test negative frequency
        with pytest.raises(ValueError, match="Frequency mentioned cannot be negative"):
            TopicInterest(topic="Test", interest_level=0.5, frequency_mentioned=-1)
    
    def test_topic_interest_serialization(self):
        """Test topic interest serialization."""
        interest = TopicInterest(
            topic="Machine Learning",
            interest_level=0.9,
            frequency_mentioned=5,
            context_keywords=["AI", "neural networks"]
        )
        
        # Test to_dict
        data = interest.to_dict()
        assert data["topic"] == "Machine Learning"
        assert data["interest_level"] == 0.9
        assert data["frequency_mentioned"] == 5
        assert data["context_keywords"] == ["AI", "neural networks"]
        
        # Test from_dict
        restored = TopicInterest.from_dict(data)
        assert restored.topic == interest.topic
        assert restored.interest_level == interest.interest_level
        assert restored.frequency_mentioned == interest.frequency_mentioned
        assert restored.context_keywords == interest.context_keywords
    
    def test_increment_frequency(self):
        """Test incrementing frequency."""
        interest = TopicInterest(topic="Test", interest_level=0.5)
        
        interest.increment_frequency()
        
        assert interest.frequency_mentioned == 1
        assert interest.last_mentioned is not None
        assert interest.updated_at is not None
    
    def test_update_interest_level(self):
        """Test updating interest level."""
        interest = TopicInterest(topic="Test", interest_level=0.5)
        
        interest.update_interest_level(0.8)
        
        assert interest.interest_level == 0.8
        assert interest.updated_at is not None
        
        # Test validation
        with pytest.raises(ValueError, match="Interest level must be between 0.0 and 1.0"):
            interest.update_interest_level(1.5)


class TestCommunicationPreferences:
    """Test CommunicationPreferences class."""
    
    def test_create_default_communication_preferences(self):
        """Test creating communication preferences with defaults."""
        prefs = CommunicationPreferences()
        
        assert prefs.prefers_step_by_step is False
        assert prefs.prefers_code_examples is True
        assert prefs.prefers_analogies is False
        assert prefs.prefers_bullet_points is False
        assert prefs.language_preference is None
        assert prefs.timezone is None
        assert prefs.confidence == 0.0
        assert isinstance(prefs.created_at, datetime)
        assert prefs.updated_at is None
    
    def test_communication_preferences_validation(self):
        """Test communication preferences validation."""
        # Test language preference too long
        with pytest.raises(ValueError, match="Language preference code too long"):
            CommunicationPreferences(language_preference="x" * 11)
        
        # Test timezone too long
        with pytest.raises(ValueError, match="Timezone string too long"):
            CommunicationPreferences(timezone="x" * 51)
        
        # Test invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            CommunicationPreferences(confidence=1.5)
    
    def test_communication_preferences_serialization(self):
        """Test communication preferences serialization."""
        prefs = CommunicationPreferences(
            prefers_step_by_step=True,
            prefers_code_examples=False,
            language_preference="en",
            timezone="UTC",
            confidence=0.6
        )
        
        # Test to_dict
        data = prefs.to_dict()
        assert data["prefers_step_by_step"] is True
        assert data["prefers_code_examples"] is False
        assert data["language_preference"] == "en"
        assert data["timezone"] == "UTC"
        assert data["confidence"] == 0.6
        
        # Test from_dict
        restored = CommunicationPreferences.from_dict(data)
        assert restored.prefers_step_by_step == prefs.prefers_step_by_step
        assert restored.prefers_code_examples == prefs.prefers_code_examples
        assert restored.language_preference == prefs.language_preference
        assert restored.timezone == prefs.timezone
        assert restored.confidence == prefs.confidence
    
    def test_update_preference(self):
        """Test updating individual preferences."""
        prefs = CommunicationPreferences()
        
        prefs.update_preference("prefers_step_by_step", True)
        assert prefs.prefers_step_by_step is True
        assert prefs.updated_at is not None
        
        # Test invalid preference
        with pytest.raises(ValueError, match="Unknown preference"):
            prefs.update_preference("invalid_preference", True)
    
    def test_get_preference_summary(self):
        """Test getting preference summary."""
        prefs = CommunicationPreferences(
            prefers_step_by_step=True,
            prefers_code_examples=False,
            language_preference="en",
            timezone="UTC",
            confidence=0.7
        )
        
        summary = prefs.get_preference_summary()
        
        assert summary["formatting"]["step_by_step"] is True
        assert summary["formatting"]["code_examples"] is False
        assert summary["localization"]["language"] == "en"
        assert summary["localization"]["timezone"] == "UTC"
        assert summary["confidence"] == 0.7


class TestUserPreferences:
    """Test UserPreferences class."""
    
    def test_create_user_preferences(self):
        """Test creating user preferences."""
        prefs = UserPreferences(user_id="user-123")
        
        assert prefs.user_id == "user-123"
        assert isinstance(prefs.response_style, ResponseStyle)
        assert prefs.topic_interests == []
        assert isinstance(prefs.communication_preferences, CommunicationPreferences)
        assert isinstance(prefs.last_updated, datetime)
        assert prefs.learning_enabled is True
        assert prefs.metadata == {}
        assert isinstance(prefs.created_at, datetime)
        assert prefs.version == 1
    
    def test_user_preferences_validation(self):
        """Test user preferences validation."""
        # Test empty user ID
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            UserPreferences(user_id="")
        
        # Test user ID too long
        long_id = "x" * 256
        with pytest.raises(ValueError, match="User ID too long"):
            UserPreferences(user_id=long_id)
        
        # Test invalid version
        with pytest.raises(ValueError, match="Version must be positive"):
            UserPreferences(user_id="user-123", version=0)
        
        # Test duplicate topics
        interests = [
            TopicInterest(topic="Python", interest_level=0.8),
            TopicInterest(topic="python", interest_level=0.7)  # Duplicate (case insensitive)
        ]
        with pytest.raises(ValueError, match="Duplicate topics found"):
            UserPreferences(user_id="user-123", topic_interests=interests)
    
    def test_get_topic_interest(self):
        """Test getting topic interest."""
        prefs = UserPreferences(user_id="user-123")
        interest = TopicInterest(topic="Python", interest_level=0.8)
        prefs.topic_interests.append(interest)
        
        # Test exact match
        found = prefs.get_topic_interest("Python")
        assert found == interest
        
        # Test case insensitive match
        found = prefs.get_topic_interest("python")
        assert found == interest
        
        # Test not found
        found = prefs.get_topic_interest("Java")
        assert found is None
    
    def test_add_or_update_topic_interest(self):
        """Test adding or updating topic interest."""
        prefs = UserPreferences(user_id="user-123")
        
        # Test adding new topic
        prefs.add_or_update_topic_interest("Python", 0.8, ["programming", "coding"])
        
        assert len(prefs.topic_interests) == 1
        interest = prefs.topic_interests[0]
        assert interest.topic == "Python"
        assert interest.interest_level == 0.8
        assert interest.frequency_mentioned == 1
        assert interest.context_keywords == ["programming", "coding"]
        
        # Test updating existing topic
        prefs.add_or_update_topic_interest("Python", 0.9, ["advanced"])
        
        assert len(prefs.topic_interests) == 1
        interest = prefs.topic_interests[0]
        assert interest.interest_level == 0.9
        assert interest.frequency_mentioned == 2
        assert set(interest.context_keywords) == {"programming", "coding", "advanced"}
    
    def test_remove_topic_interest(self):
        """Test removing topic interest."""
        prefs = UserPreferences(user_id="user-123")
        prefs.topic_interests.append(TopicInterest(topic="Python", interest_level=0.8))
        prefs.topic_interests.append(TopicInterest(topic="Java", interest_level=0.6))
        
        # Test successful removal
        result = prefs.remove_topic_interest("Python")
        assert result is True
        assert len(prefs.topic_interests) == 1
        assert prefs.topic_interests[0].topic == "Java"
        
        # Test removal of non-existent topic
        result = prefs.remove_topic_interest("C++")
        assert result is False
        assert len(prefs.topic_interests) == 1
    
    def test_get_top_interests(self):
        """Test getting top interests."""
        prefs = UserPreferences(user_id="user-123")
        
        # Add interests with different levels and frequencies
        interests = [
            TopicInterest(topic="Python", interest_level=0.9, frequency_mentioned=10),
            TopicInterest(topic="Java", interest_level=0.8, frequency_mentioned=5),
            TopicInterest(topic="JavaScript", interest_level=0.7, frequency_mentioned=15),
            TopicInterest(topic="C++", interest_level=0.6, frequency_mentioned=3)
        ]
        prefs.topic_interests.extend(interests)
        
        # Test getting top 2 interests
        top_interests = prefs.get_top_interests(2)
        assert len(top_interests) == 2
        assert top_interests[0].topic == "Python"  # Highest interest level
        assert top_interests[1].topic == "Java"    # Second highest interest level
    
    def test_update_response_style(self):
        """Test updating response style."""
        prefs = UserPreferences(user_id="user-123")
        
        prefs.update_response_style(
            style_type=ResponseStyleType.TECHNICAL,
            confidence=0.8
        )
        
        assert prefs.response_style.style_type == ResponseStyleType.TECHNICAL
        assert prefs.response_style.confidence == 0.8
        assert prefs.response_style.updated_at is not None
    
    def test_update_communication_preferences(self):
        """Test updating communication preferences."""
        prefs = UserPreferences(user_id="user-123")
        
        prefs.update_communication_preferences(
            prefers_step_by_step=True,
            language_preference="en"
        )
        
        assert prefs.communication_preferences.prefers_step_by_step is True
        assert prefs.communication_preferences.language_preference == "en"
    
    def test_get_preference_summary(self):
        """Test getting comprehensive preference summary."""
        prefs = UserPreferences(user_id="user-123")
        prefs.add_or_update_topic_interest("Python", 0.9)
        prefs.add_or_update_topic_interest("Java", 0.7)
        
        summary = prefs.get_preference_summary()
        
        assert summary["user_id"] == "user-123"
        assert "response_style" in summary
        assert "communication" in summary
        assert "top_interests" in summary
        assert summary["learning_enabled"] is True
        assert "last_updated" in summary
        assert summary["version"] == 1
        
        # Check top interests
        assert len(summary["top_interests"]) == 2
        assert summary["top_interests"][0]["topic"] == "Python"
        assert summary["top_interests"][0]["level"] == 0.9
    
    def test_user_preferences_serialization(self):
        """Test user preferences serialization."""
        prefs = UserPreferences(user_id="user-123")
        prefs.add_or_update_topic_interest("Python", 0.8)
        prefs.update_response_style(style_type=ResponseStyleType.TECHNICAL)
        
        # Test to_dict
        data = prefs.to_dict()
        assert data["user_id"] == "user-123"
        assert "response_style" in data
        assert "topic_interests" in data
        assert "communication_preferences" in data
        assert len(data["topic_interests"]) == 1
        
        # Test from_dict
        restored = UserPreferences.from_dict(data)
        assert restored.user_id == prefs.user_id
        assert len(restored.topic_interests) == 1
        assert restored.topic_interests[0].topic == "Python"
        assert restored.response_style.style_type == ResponseStyleType.TECHNICAL
    
    def test_user_preferences_json_serialization(self):
        """Test user preferences JSON serialization."""
        prefs = UserPreferences(user_id="user-123")
        prefs.add_or_update_topic_interest("Python", 0.8)
        
        # Test to_json
        json_str = prefs.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        restored = UserPreferences.from_json(json_str)
        assert restored.user_id == prefs.user_id
        assert len(restored.topic_interests) == 1
        assert restored.topic_interests[0].topic == "Python"
    
    def test_user_preferences_clone(self):
        """Test user preferences cloning."""
        prefs = UserPreferences(user_id="user-123")
        prefs.add_or_update_topic_interest("Python", 0.8)
        
        cloned = prefs.clone()
        
        # Should be equal but different objects
        assert cloned.user_id == prefs.user_id
        assert len(cloned.topic_interests) == len(prefs.topic_interests)
        assert cloned is not prefs
        assert cloned.topic_interests is not prefs.topic_interests
    
    def test_user_preferences_merge(self):
        """Test user preferences merging."""
        prefs1 = UserPreferences(user_id="user-123")
        prefs1.add_or_update_topic_interest("Python", 0.8)
        prefs1.add_or_update_topic_interest("Java", 0.6)
        prefs1.response_style.confidence = 0.7
        
        prefs2 = UserPreferences(user_id="user-123")
        prefs2.add_or_update_topic_interest("Python", 0.9)  # Higher interest
        prefs2.add_or_update_topic_interest("JavaScript", 0.7)  # New topic
        prefs2.response_style.confidence = 0.8  # Higher confidence
        
        merged = prefs1.merge_with(prefs2)
        
        assert merged.user_id == "user-123"
        assert len(merged.topic_interests) == 3  # Python, Java, JavaScript
        
        # Python should have averaged interest level
        python_interest = merged.get_topic_interest("Python")
        assert python_interest.interest_level == 0.85  # (0.8 + 0.9) / 2
        
        # Should use higher confidence response style
        assert merged.response_style.confidence == 0.8
    
    def test_user_preferences_merge_different_users(self):
        """Test that merging preferences from different users fails."""
        prefs1 = UserPreferences(user_id="user-123")
        prefs2 = UserPreferences(user_id="user-456")
        
        with pytest.raises(ValueError, match="Cannot merge preferences from different users"):
            prefs1.merge_with(prefs2)
    
    def test_timestamp_handling(self):
        """Test timestamp handling with naive datetimes."""
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        
        prefs = UserPreferences(
            user_id="user-123",
            last_updated=naive_time,
            created_at=naive_time
        )
        
        assert prefs.last_updated.tzinfo == timezone.utc
        assert prefs.created_at.tzinfo == timezone.utc
    
    def test_preference_tracking_workflow(self):
        """Test a complete preference tracking workflow."""
        # Create user preferences
        prefs = UserPreferences(user_id="user-123")
        
        # User shows interest in Python programming
        prefs.add_or_update_topic_interest("Python", 0.7, ["programming", "scripting"])
        
        # User prefers technical responses
        prefs.update_response_style(
            style_type=ResponseStyleType.TECHNICAL,
            tone=CommunicationTone.PROFESSIONAL,
            confidence=0.6
        )
        
        # User prefers step-by-step explanations
        prefs.update_communication_preferences(
            prefers_step_by_step=True,
            prefers_code_examples=True
        )
        
        # User mentions Python again with higher interest
        prefs.add_or_update_topic_interest("Python", 0.9, ["advanced", "frameworks"])
        
        # User shows interest in new topic
        prefs.add_or_update_topic_interest("Machine Learning", 0.8, ["AI", "data science"])
        
        # Verify final state
        assert len(prefs.topic_interests) == 2
        
        python_interest = prefs.get_topic_interest("Python")
        assert python_interest.interest_level == 0.9
        assert python_interest.frequency_mentioned == 2
        assert set(python_interest.context_keywords) == {"programming", "scripting", "advanced", "frameworks"}
        
        ml_interest = prefs.get_topic_interest("Machine Learning")
        assert ml_interest.interest_level == 0.8
        assert ml_interest.frequency_mentioned == 1
        
        # Check response style
        assert prefs.response_style.style_type == ResponseStyleType.TECHNICAL
        assert prefs.response_style.tone == CommunicationTone.PROFESSIONAL
        
        # Check communication preferences
        assert prefs.communication_preferences.prefers_step_by_step is True
        assert prefs.communication_preferences.prefers_code_examples is True
        
        # Get summary
        summary = prefs.get_preference_summary()
        assert len(summary["top_interests"]) == 2
        assert summary["top_interests"][0]["topic"] == "Python"  # Higher interest level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])