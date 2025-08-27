"""
Unit tests for preference update and learning functionality.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from src.memory.services.preference_engine import PreferenceEngine
from src.memory.models.preferences import (
    UserPreferences, ResponseStyle, ResponseStyleType, CommunicationTone,
    CommunicationPreferences
)
from src.memory.models.common import UserFeedback, FeedbackType


class TestPreferenceLearning:
    """Test cases for preference learning and update functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PreferenceEngine()
    
    def create_test_preferences(self, user_id: str = "test_user") -> UserPreferences:
        """Helper to create test preferences."""
        return UserPreferences(
            user_id=user_id,
            response_style=ResponseStyle(
                style_type=ResponseStyleType.CONVERSATIONAL,
                tone=CommunicationTone.HELPFUL,
                confidence=0.5
            ),
            communication_preferences=CommunicationPreferences(
                confidence=0.5
            )
        )
    
    @pytest.mark.asyncio
    async def test_update_preferences_positive_feedback(self):
        """Test updating preferences with positive feedback."""
        # Set up initial preferences
        preferences = self.create_test_preferences()
        self.engine._preferences_cache["test_user"] = preferences
        
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.POSITIVE,
            rating=5
        )
        
        initial_confidence = preferences.response_style.confidence
        
        await self.engine.update_preferences("test_user", feedback)
        
        updated_preferences = await self.engine.get_preferences("test_user")
        
        # Confidence should increase
        assert updated_preferences.response_style.confidence > initial_confidence
        assert updated_preferences.last_updated is not None
    
    @pytest.mark.asyncio
    async def test_update_preferences_negative_feedback(self):
        """Test updating preferences with negative feedback."""
        # Set up initial preferences
        preferences = self.create_test_preferences()
        preferences.response_style.confidence = 0.8
        self.engine._preferences_cache["test_user"] = preferences
        
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.NEGATIVE,
            rating=1
        )
        
        initial_confidence = preferences.response_style.confidence
        
        await self.engine.update_preferences("test_user", feedback)
        
        updated_preferences = await self.engine.get_preferences("test_user")
        
        # Confidence should decrease
        assert updated_preferences.response_style.confidence < initial_confidence
    
    @pytest.mark.asyncio
    async def test_update_preferences_correction_feedback(self):
        """Test updating preferences with correction feedback."""
        # Set up initial preferences
        preferences = self.create_test_preferences()
        self.engine._preferences_cache["test_user"] = preferences
        
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.CORRECTION,
            feedback_text="Please make your responses shorter and more concise"
        )
        
        await self.engine.update_preferences("test_user", feedback)
        
        updated_preferences = await self.engine.get_preferences("test_user")
        
        # Should adapt to correction
        assert updated_preferences.response_style.style_type == ResponseStyleType.CONCISE
        assert updated_preferences.response_style.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_process_correction_feedback_length_reduction(self):
        """Test processing correction feedback that reduces response length."""
        original_response = "This is a very long and detailed response that contains a lot of information and explanations that might be unnecessary for the user's needs."
        corrected_response = "This is a concise response."
        
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response=original_response,
            corrected_response=corrected_response,
            feedback_text="Too verbose, please be more concise"
        )
        
        preferences = await self.engine.get_preferences("test_user")
        
        # Should prefer concise style
        assert preferences.response_style.style_type == ResponseStyleType.CONCISE
        assert preferences.response_style.preferred_length == "short"
        assert preferences.response_style.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_process_correction_feedback_length_increase(self):
        """Test processing correction feedback that increases response length."""
        original_response = "Short response."
        corrected_response = "This is a much more detailed and comprehensive response that provides extensive explanations and examples to help the user understand the topic better."
        
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response=original_response,
            corrected_response=corrected_response,
            feedback_text="Please provide more detail and elaborate on the topic"
        )
        
        preferences = await self.engine.get_preferences("test_user")
        
        # Should prefer detailed style
        assert preferences.response_style.style_type == ResponseStyleType.DETAILED
        assert preferences.response_style.preferred_length == "long"
        assert preferences.response_style.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_process_correction_feedback_formatting_changes(self):
        """Test processing correction feedback with formatting changes."""
        original_response = "First do this, then do that, finally complete the task."
        corrected_response = "1. Do this\n2. Do that\n3. Complete the task"
        
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response=original_response,
            corrected_response=corrected_response,
            feedback_text="Please format as numbered steps"
        )
        
        preferences = await self.engine.get_preferences("test_user")
        
        # Should prefer step-by-step formatting
        assert preferences.communication_preferences.prefers_step_by_step is True
        assert preferences.communication_preferences.confidence >= 0.2
    
    @pytest.mark.asyncio
    async def test_process_correction_feedback_tone_changes(self):
        """Test processing correction feedback with tone changes."""
        original_response = "You need to do this."
        corrected_response = "I hope this helps! Please try doing this, and thank you for your question."
        
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response=original_response,
            corrected_response=corrected_response,
            feedback_text="Please be more friendly and polite"
        )
        
        preferences = await self.engine.get_preferences("test_user")
        
        # Should prefer friendly tone
        assert preferences.response_style.tone == CommunicationTone.FRIENDLY
        assert preferences.response_style.confidence >= 0.5
    
    @pytest.mark.asyncio
    async def test_analyze_correction_differences(self):
        """Test analyzing differences between original and corrected responses."""
        original = "This works by using a simple method."
        corrected = "1. This functions algorithmically\n2. It implements a sophisticated approach\n• Key benefits include efficiency"
        
        corrections = await self.engine._analyze_correction_differences(original, corrected)
        
        assert corrections['length_change'] > 0
        assert 'prefers_numbered_lists' in corrections['format_changes']
        assert 'prefers_bullet_points' in corrections['format_changes']
    
    @pytest.mark.asyncio
    async def test_load_preferences_from_cache(self):
        """Test loading preferences from cache."""
        # Set up cached preferences
        preferences = self.create_test_preferences()
        self.engine._preferences_cache["test_user"] = preferences
        
        loaded_preferences = await self.engine.load_preferences("test_user")
        
        assert loaded_preferences.user_id == "test_user"
        assert loaded_preferences == preferences
    
    @pytest.mark.asyncio
    async def test_load_preferences_not_cached(self):
        """Test loading preferences when not in cache."""
        loaded_preferences = await self.engine.load_preferences("new_user")
        
        assert loaded_preferences.user_id == "new_user"
        assert loaded_preferences.response_style.confidence == 0.0
        assert "new_user" in self.engine._preferences_cache
    
    @pytest.mark.asyncio
    async def test_get_preference_insights(self):
        """Test getting preference insights."""
        # Set up preferences with some data
        preferences = self.create_test_preferences()
        preferences.response_style.confidence = 0.8
        preferences.communication_preferences.confidence = 0.7
        self.engine._preferences_cache["test_user"] = preferences
        
        insights = await self.engine.get_preference_insights("test_user")
        
        assert insights['user_id'] == "test_user"
        assert insights['learning_enabled'] is True
        assert insights['confidence_scores']['response_style'] == 0.8
        assert insights['confidence_scores']['communication'] == 0.7
        assert 'preferences_summary' in insights
        assert 'top_topics' in insights
    
    @pytest.mark.asyncio
    async def test_reset_preferences(self):
        """Test resetting user preferences."""
        # Set up modified preferences
        preferences = self.create_test_preferences()
        preferences.response_style.style_type = ResponseStyleType.TECHNICAL
        preferences.response_style.confidence = 0.9
        self.engine._preferences_cache["test_user"] = preferences
        
        await self.engine.reset_preferences("test_user")
        
        reset_preferences = await self.engine.get_preferences("test_user")
        
        # Should be back to defaults
        assert reset_preferences.response_style.style_type == ResponseStyleType.CONVERSATIONAL
        assert reset_preferences.response_style.confidence == 0.0
        assert reset_preferences.communication_preferences.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_export_preferences(self):
        """Test exporting user preferences."""
        # Set up preferences
        preferences = self.create_test_preferences()
        self.engine._preferences_cache["test_user"] = preferences
        
        exported_data = await self.engine.export_preferences("test_user")
        
        assert exported_data['user_id'] == "test_user"
        assert 'response_style' in exported_data
        assert 'communication_preferences' in exported_data
        assert 'topic_interests' in exported_data
    
    @pytest.mark.asyncio
    async def test_import_preferences(self):
        """Test importing user preferences."""
        # Create test data
        preferences_data = {
            'user_id': 'imported_user',
            'response_style': {
                'style_type': 'technical',
                'tone': 'professional',
                'confidence': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            'communication_preferences': {
                'prefers_step_by_step': True,
                'prefers_code_examples': True,
                'confidence': 0.7,
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            'topic_interests': [],
            'learning_enabled': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'version': 1
        }
        
        await self.engine.import_preferences("test_user", preferences_data)
        
        imported_preferences = await self.engine.get_preferences("test_user")
        
        assert imported_preferences.user_id == "test_user"  # Should use provided user_id
        assert imported_preferences.response_style.style_type == ResponseStyleType.TECHNICAL
        assert imported_preferences.response_style.tone == CommunicationTone.PROFESSIONAL
        assert imported_preferences.communication_preferences.prefers_step_by_step is True
    
    @pytest.mark.asyncio
    async def test_process_feedback_text_step_by_step(self):
        """Test processing feedback text for step-by-step preference."""
        preferences = self.create_test_preferences()
        
        await self.engine._process_feedback_text(preferences, "Please break it down step by step")
        
        assert preferences.communication_preferences.prefers_step_by_step is True
        assert preferences.communication_preferences.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_process_feedback_text_examples(self):
        """Test processing feedback text for examples preference."""
        preferences = self.create_test_preferences()
        
        await self.engine._process_feedback_text(preferences, "Can you show me some examples?")
        
        assert preferences.communication_preferences.prefers_code_examples is True
        assert preferences.communication_preferences.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_process_feedback_text_tone_casual(self):
        """Test processing feedback text for casual tone preference."""
        preferences = self.create_test_preferences()
        
        await self.engine._process_feedback_text(preferences, "Too formal, please be more casual and friendly")
        
        assert preferences.response_style.tone == CommunicationTone.FRIENDLY
    
    @pytest.mark.asyncio
    async def test_process_feedback_text_tone_professional(self):
        """Test processing feedback text for professional tone preference."""
        preferences = self.create_test_preferences()
        
        await self.engine._process_feedback_text(preferences, "Please use more professional language")
        
        assert preferences.response_style.tone == CommunicationTone.PROFESSIONAL
    
    @pytest.mark.asyncio
    async def test_error_handling_in_update_preferences(self):
        """Test error handling during preference updates."""
        # Mock _persist_preferences to raise an exception
        with patch.object(self.engine, '_persist_preferences', side_effect=Exception("Storage error")):
            feedback = UserFeedback(
                user_id="test_user",
                message_id="msg_123",
                feedback_type=FeedbackType.POSITIVE
            )
            
            # Should raise the exception
            with pytest.raises(Exception, match="Storage error"):
                await self.engine.update_preferences("test_user", feedback)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_correction_processing(self):
        """Test error handling during correction processing."""
        # Mock _analyze_correction_differences to raise an exception
        with patch.object(self.engine, '_analyze_correction_differences', side_effect=Exception("Analysis error")):
            # Should not raise exception, should handle gracefully
            await self.engine.process_correction_feedback(
                user_id="test_user",
                original_response="Original",
                corrected_response="Corrected"
            )
            
            # Should still be able to get preferences
            preferences = await self.engine.get_preferences("test_user")
            assert preferences.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_persist_preferences_placeholder(self):
        """Test the persistence placeholder method."""
        preferences = self.create_test_preferences()
        
        # Should not raise exception (it's a placeholder)
        await self.engine._persist_preferences("test_user", preferences)
    
    @pytest.mark.asyncio
    async def test_multiple_corrections_accumulate(self):
        """Test that multiple corrections accumulate confidence."""
        # Process first correction
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response="Long response here",
            corrected_response="Short.",
            feedback_text="Too long"
        )
        
        first_confidence = (await self.engine.get_preferences("test_user")).response_style.confidence
        
        # Process second similar correction
        await self.engine.process_correction_feedback(
            user_id="test_user",
            original_response="Another long response",
            corrected_response="Brief.",
            feedback_text="Still too verbose"
        )
        
        second_confidence = (await self.engine.get_preferences("test_user")).response_style.confidence
        
        # Confidence should increase
        assert second_confidence > first_confidence
        assert (await self.engine.get_preferences("test_user")).response_style.style_type == ResponseStyleType.CONCISE


if __name__ == "__main__":
    pytest.main([__file__])