"""
Unit tests for preference application logic.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.memory.services.preference_engine import PreferenceEngine
from src.memory.models.preferences import (
    UserPreferences, ResponseStyle, ResponseStyleType, CommunicationTone,
    CommunicationPreferences, TopicInterest
)


class TestPreferenceApplication:
    """Test cases for preference application logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PreferenceEngine()
    
    def create_test_preferences(self, 
                               style_type: ResponseStyleType = ResponseStyleType.CONVERSATIONAL,
                               tone: CommunicationTone = CommunicationTone.HELPFUL,
                               style_confidence: float = 0.8,
                               comm_confidence: float = 0.8,
                               **comm_prefs) -> UserPreferences:
        """Helper to create test preferences."""
        response_style = ResponseStyle(
            style_type=style_type,
            tone=tone,
            confidence=style_confidence
        )
        
        communication_preferences = CommunicationPreferences(
            confidence=comm_confidence,
            **comm_prefs
        )
        
        return UserPreferences(
            user_id="test_user",
            response_style=response_style,
            communication_preferences=communication_preferences
        )
    
    @pytest.mark.asyncio
    async def test_apply_preferences_no_preferences(self):
        """Test applying preferences when user has no stored preferences."""
        response = "This is a test response."
        
        result = await self.engine.apply_preferences("unknown_user", response)
        
        # Should return original response when no preferences exist
        assert result == response
    
    @pytest.mark.asyncio
    async def test_apply_preferences_learning_disabled(self):
        """Test applying preferences when learning is disabled."""
        preferences = self.create_test_preferences()
        preferences.learning_enabled = False
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This is a test response."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should return original response when learning is disabled
        assert result == response
    
    @pytest.mark.asyncio
    async def test_apply_preferences_low_confidence(self):
        """Test applying preferences with low confidence scores."""
        preferences = self.create_test_preferences(
            style_confidence=0.1,
            comm_confidence=0.1
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This is a test response."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should return original response when confidence is too low
        assert result == response
    
    @pytest.mark.asyncio
    async def test_apply_concise_style(self):
        """Test applying concise response style."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.CONCISE,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = ("As I mentioned before, this is a very long response that contains "
                   "redundant information. It should be noted that this response is "
                   "unnecessarily verbose and could be shortened significantly.")
        
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should be shorter and remove redundant phrases
        assert len(result) < len(response)
        assert "As I mentioned before," not in result
        assert "It should be noted that" not in result
    
    @pytest.mark.asyncio
    async def test_apply_detailed_style(self):
        """Test applying detailed response style."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.DETAILED,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This is a short response."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should be longer with additional explanations
        assert len(result) > len(response)
        assert "This is important because" in result or "Would you like me to elaborate" in result
    
    @pytest.mark.asyncio
    async def test_apply_technical_style(self):
        """Test applying technical response style."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.TECHNICAL,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This system works by using a simple method."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should use more technical language
        assert "algorithmically" in result or "implements" in result
    
    @pytest.mark.asyncio
    async def test_apply_casual_style(self):
        """Test applying casual response style."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.CASUAL,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "You need to utilize the functionality to implement the algorithm with these parameters."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should use more casual language
        assert "use" in result
        assert "feature" in result or "method" in result
        assert "settings" in result
    
    @pytest.mark.asyncio
    async def test_apply_friendly_tone(self):
        """Test applying friendly tone."""
        preferences = self.create_test_preferences(
            tone=CommunicationTone.FRIENDLY,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "Here is the information you requested."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should add friendly elements
        assert "hope this helps" in result.lower() or any(word in result.lower() for word in ['glad', 'happy', 'great'])
    
    @pytest.mark.asyncio
    async def test_apply_professional_tone(self):
        """Test applying professional tone."""
        preferences = self.create_test_preferences(
            tone=CommunicationTone.PROFESSIONAL,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "Hey there! Thanks! No problem with helping you."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should use more professional language
        assert "Hey" not in result
        assert "Hello" in result or "Good day" in result
        assert "Thank you." in result
    
    @pytest.mark.asyncio
    async def test_apply_direct_tone(self):
        """Test applying direct tone."""
        preferences = self.create_test_preferences(
            tone=CommunicationTone.DIRECT,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "I think you might want to consider perhaps trying this approach."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should remove hedging language
        assert "I think" not in result
        assert "might want to" not in result
        assert "perhaps" not in result
    
    @pytest.mark.asyncio
    async def test_apply_encouraging_tone(self):
        """Test applying encouraging tone."""
        preferences = self.create_test_preferences(
            tone=CommunicationTone.ENCOURAGING,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "Here is how to solve this problem."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should add encouraging phrases
        assert any(phrase in result for phrase in [
            "You're on the right track!", "Great question!", "You can do this!", "Keep up the good work!"
        ])
    
    @pytest.mark.asyncio
    async def test_apply_step_by_step_preference(self):
        """Test applying step-by-step communication preference."""
        preferences = self.create_test_preferences(
            prefers_step_by_step=True,
            comm_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "First, you need to set up the environment. Then, install the dependencies. Finally, run the application."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should format as numbered steps
        assert "1." in result
        assert "2." in result
        assert "3." in result
    
    @pytest.mark.asyncio
    async def test_apply_code_examples_preference(self):
        """Test applying code examples preference."""
        preferences = self.create_test_preferences(
            prefers_code_examples=True,
            comm_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "You can use Python programming to solve this."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should mention examples
        assert "example" in result.lower()
    
    @pytest.mark.asyncio
    async def test_apply_analogies_preference(self):
        """Test applying analogies preference."""
        preferences = self.create_test_preferences(
            prefers_analogies=True,
            comm_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This is a complex algorithm that processes data efficiently."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should add analogy suggestions
        assert "like" in result.lower() or "think of it" in result.lower()
    
    @pytest.mark.asyncio
    async def test_apply_bullet_points_preference(self):
        """Test applying bullet points preference."""
        preferences = self.create_test_preferences(
            prefers_bullet_points=True,
            comm_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "1. First item\n2. Second item\n3. Third item"
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should convert to bullet points
        assert "•" in result
        assert "1." not in result
    
    @pytest.mark.asyncio
    async def test_apply_multiple_preferences(self):
        """Test applying multiple preferences simultaneously."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.DETAILED,
            tone=CommunicationTone.FRIENDLY,
            style_confidence=0.8,
            comm_confidence=0.8,
            prefers_step_by_step=True,
            prefers_code_examples=True
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "First, write the code. Then, test it."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should apply multiple modifications
        assert len(result) > len(response)  # Detailed style
        assert "hope" in result.lower() or "glad" in result.lower()  # Friendly tone
        assert "1." in result and "2." in result  # Step-by-step
        assert "example" in result.lower()  # Code examples
    
    @pytest.mark.asyncio
    async def test_apply_preferences_error_handling(self):
        """Test error handling during preference application."""
        preferences = self.create_test_preferences()
        self.engine._preferences_cache["test_user"] = preferences
        
        # Mock a method to raise an exception
        with patch.object(self.engine, '_apply_response_style', side_effect=Exception("Test error")):
            response = "This is a test response."
            result = await self.engine.apply_preferences("test_user", response)
            
            # Should return original response on error
            assert result == response
    
    @pytest.mark.asyncio
    async def test_length_adjustment_short(self):
        """Test adjusting response length to short."""
        preferences = self.create_test_preferences(style_confidence=0.8)
        preferences.response_style.preferred_length = "short"
        self.engine._preferences_cache["test_user"] = preferences
        
        long_response = "This is a very long response " * 20  # Make it long
        result = await self.engine.apply_preferences("test_user", long_response)
        
        # Should be shorter
        assert len(result) < len(long_response)
    
    @pytest.mark.asyncio
    async def test_length_adjustment_long(self):
        """Test adjusting response length to long."""
        preferences = self.create_test_preferences(style_confidence=0.8)
        preferences.response_style.preferred_length = "long"
        self.engine._preferences_cache["test_user"] = preferences
        
        short_response = "Short response."
        result = await self.engine.apply_preferences("test_user", short_response)
        
        # Should be longer
        assert len(result) > len(short_response)
    
    @pytest.mark.asyncio
    async def test_preserve_original_on_no_modifications(self):
        """Test that original response is preserved when no modifications are needed."""
        preferences = self.create_test_preferences(
            style_type=ResponseStyleType.CONVERSATIONAL,
            tone=CommunicationTone.HELPFUL,
            style_confidence=0.8
        )
        self.engine._preferences_cache["test_user"] = preferences
        
        response = "This is a well-formatted response that doesn't need changes."
        result = await self.engine.apply_preferences("test_user", response)
        
        # Should be similar to original (minor tone adjustments might occur)
        assert len(result) >= len(response) * 0.8  # Allow for minor modifications


if __name__ == "__main__":
    pytest.main([__file__])