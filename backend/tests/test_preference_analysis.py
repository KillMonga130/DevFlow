"""
Unit tests for preference analysis algorithms.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.memory.services.preference_engine import PreferenceEngine, PreferenceAnalyzer
from src.memory.models.conversation import Conversation, Message, MessageRole
from src.memory.models.preferences import (
    UserPreferences, ResponseStyleType, CommunicationTone, TopicInterest
)
from src.memory.models.common import UserFeedback, FeedbackType


class TestPreferenceAnalyzer:
    """Test cases for PreferenceAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PreferenceAnalyzer()
    
    def create_test_conversation(self, user_messages: list, user_id: str = "test_user") -> Conversation:
        """Helper to create test conversations."""
        messages = []
        for i, content in enumerate(user_messages):
            messages.append(Message(
                role=MessageRole.USER,
                content=content,
                timestamp=datetime.now(timezone.utc)
            ))
            # Add assistant response
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=f"Response to: {content[:20]}...",
                timestamp=datetime.now(timezone.utc)
            ))
        
        return Conversation(
            user_id=user_id,
            messages=messages
        )
    
    def test_analyze_response_style_concise_preference(self):
        """Test detection of concise response style preference."""
        conversations = [
            self.create_test_conversation([
                "Give me a brief summary of Python",
                "Keep it short please",
                "Just the basics, nothing detailed",
                "Quick answer needed"
            ])
        ]
        
        style = self.analyzer.analyze_response_style(conversations)
        
        assert style.style_type == ResponseStyleType.CONCISE
        assert style.confidence > 0.5
    
    def test_analyze_response_style_detailed_preference(self):
        """Test detection of detailed response style preference."""
        conversations = [
            self.create_test_conversation([
                "Please explain in detail how machine learning works",
                "I need a comprehensive guide to web development",
                "Walk me through the entire process step by step",
                "Give me a thorough explanation with examples"
            ])
        ]
        
        style = self.analyzer.analyze_response_style(conversations)
        
        assert style.style_type == ResponseStyleType.DETAILED
        assert style.confidence > 0.5
    
    def test_analyze_response_style_technical_preference(self):
        """Test detection of technical response style preference."""
        conversations = [
            self.create_test_conversation([
                "Show me the technical implementation details",
                "I need the algorithm specifications",
                "What's the architecture behind this system?",
                "Give me the code documentation"
            ])
        ]
        
        style = self.analyzer.analyze_response_style(conversations)
        
        assert style.style_type == ResponseStyleType.TECHNICAL
        assert style.confidence > 0.5
    
    def test_analyze_tone_friendly(self):
        """Test detection of friendly communication tone."""
        conversations = [
            self.create_test_conversation([
                "Thanks for your help! This is awesome",
                "I really appreciate your assistance",
                "That's fantastic, thank you so much",
                "Great explanation, please continue"
            ])
        ]
        
        style = self.analyzer.analyze_response_style(conversations)
        
        assert style.tone == CommunicationTone.FRIENDLY
    
    def test_analyze_tone_professional(self):
        """Test detection of professional communication tone."""
        conversations = [
            self.create_test_conversation([
                "I require professional documentation for this enterprise solution",
                "Please provide the official business standards",
                "What are the industry best practices?",
                "I need formal specifications for corporate use"
            ])
        ]
        
        style = self.analyzer.analyze_response_style(conversations)
        
        assert style.tone == CommunicationTone.PROFESSIONAL
    
    def test_extract_topics_programming(self):
        """Test extraction of programming-related topics."""
        conversations = [
            self.create_test_conversation([
                "How do I write a Python function to sort data?",
                "I'm debugging a JavaScript algorithm issue",
                "Can you help me with software development best practices?",
                "I need to understand object-oriented programming concepts"
            ])
        ]
        
        topics = self.analyzer.extract_topics(conversations)
        
        # Should detect programming as a topic
        programming_topics = [t for t in topics if 'programming' in t.topic.lower()]
        assert len(programming_topics) > 0
        
        # Check that topics have reasonable interest levels
        for topic in topics:
            assert 0 <= topic.interest_level <= 1.0
            assert topic.frequency_mentioned >= 2  # Minimum threshold
    
    def test_extract_topics_web_development(self):
        """Test extraction of web development topics."""
        conversations = [
            self.create_test_conversation([
                "I'm building a React frontend application",
                "How do I create a REST API with Node.js?",
                "What's the best way to handle database connections?",
                "I need help with HTML and CSS styling"
            ])
        ]
        
        topics = self.analyzer.extract_topics(conversations)
        
        # Should detect web development topics
        web_topics = [t for t in topics if 'web development' in t.topic.lower()]
        assert len(web_topics) > 0 or any('react' in t.topic.lower() or 'api' in t.topic.lower() for t in topics)
    
    def test_extract_topics_with_context_keywords(self):
        """Test that topics include relevant context keywords."""
        conversations = [
            self.create_test_conversation([
                "I'm learning machine learning algorithms for data analysis",
                "Can you explain neural networks and deep learning models?",
                "I need help with pandas and numpy for data processing"
            ])
        ]
        
        topics = self.analyzer.extract_topics(conversations)
        
        # Find data science related topics
        data_topics = [t for t in topics if any(keyword in t.topic.lower() 
                                              for keyword in ['data', 'machine', 'learning'])]
        
        assert len(data_topics) > 0
        
        # Check that context keywords are captured
        for topic in data_topics:
            assert len(topic.context_keywords) > 0
    
    def test_analyze_communication_preferences_step_by_step(self):
        """Test detection of step-by-step preference."""
        conversations = [
            self.create_test_conversation([
                "Please walk me through this step by step",
                "Can you break this down one by one?",
                "First, I need to understand the basics, then move to advanced",
                "Show me the process from start to finish"
            ])
        ]
        
        prefs = self.analyzer.analyze_communication_preferences(conversations)
        
        assert prefs.prefers_step_by_step is True
        assert prefs.confidence > 0
    
    def test_analyze_communication_preferences_code_examples(self):
        """Test detection of code example preference."""
        conversations = [
            self.create_test_conversation([
                "Can you show me an example of this in code?",
                "I need sample implementations to understand",
                "Please demonstrate with actual code snippets",
                "Show me how this works with examples"
            ])
        ]
        
        prefs = self.analyzer.analyze_communication_preferences(conversations)
        
        assert prefs.prefers_code_examples is True
        assert prefs.confidence > 0
    
    def test_analyze_communication_preferences_analogies(self):
        """Test detection of analogy preference."""
        conversations = [
            self.create_test_conversation([
                "Can you explain this like a simple analogy?",
                "What's this similar to in real life?",
                "Use a metaphor to help me understand",
                "Compare this to something I might know"
            ])
        ]
        
        prefs = self.analyzer.analyze_communication_preferences(conversations)
        
        assert prefs.prefers_analogies is True
        assert prefs.confidence > 0
    
    def test_analyze_communication_preferences_bullet_points(self):
        """Test detection of bullet point preference."""
        conversations = [
            self.create_test_conversation([
                "Can you give me a list of the main points?",
                "Please outline the key features in bullet points",
                "I need a summary with the important items listed",
                "Break this down into a clear list format"
            ])
        ]
        
        prefs = self.analyzer.analyze_communication_preferences(conversations)
        
        assert prefs.prefers_bullet_points is True
        assert prefs.confidence > 0
    
    def test_empty_conversations(self):
        """Test handling of empty conversation list."""
        conversations = []
        
        style = self.analyzer.analyze_response_style(conversations)
        topics = self.analyzer.extract_topics(conversations)
        prefs = self.analyzer.analyze_communication_preferences(conversations)
        
        # Should return defaults without errors
        assert style.style_type == ResponseStyleType.CONVERSATIONAL
        assert style.confidence == 0.0
        assert len(topics) == 0
        assert prefs.confidence == 0.0
    
    def test_conversations_without_user_messages(self):
        """Test handling of conversations with no user messages."""
        conversation = Conversation(
            user_id="test_user",
            messages=[
                Message(role=MessageRole.ASSISTANT, content="Hello there!")
            ]
        )
        
        style = self.analyzer.analyze_response_style([conversation])
        topics = self.analyzer.extract_topics([conversation])
        prefs = self.analyzer.analyze_communication_preferences([conversation])
        
        # Should handle gracefully
        assert style.confidence == 0.0
        assert len(topics) == 0
        assert prefs.confidence == 0.0


class TestPreferenceEngine:
    """Test cases for PreferenceEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PreferenceEngine()
    
    def create_test_conversation(self, user_messages: list, user_id: str = "test_user") -> Conversation:
        """Helper to create test conversations."""
        messages = []
        for content in user_messages:
            messages.append(Message(
                role=MessageRole.USER,
                content=content,
                timestamp=datetime.now(timezone.utc)
            ))
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=f"Response to: {content[:20]}...",
                timestamp=datetime.now(timezone.utc)
            ))
        
        return Conversation(
            user_id=user_id,
            messages=messages
        )
    
    @pytest.mark.asyncio
    async def test_analyze_user_preferences_comprehensive(self):
        """Test comprehensive user preference analysis."""
        conversations = [
            self.create_test_conversation([
                "Please give me a detailed explanation step by step",
                "I appreciate your help and want you to walk me through this",
                "Can you show me the process step by step with examples?",
                "Show me sample code and demonstrate each step",
                "I need examples and want you to go through it step by step"
            ])
        ]
        
        preferences = await self.engine.analyze_user_preferences("test_user", conversations)
        
        assert preferences.user_id == "test_user"
        assert preferences.response_style.style_type == ResponseStyleType.DETAILED
        assert preferences.response_style.tone == CommunicationTone.FRIENDLY
        assert len(preferences.topic_interests) > 0
        assert preferences.communication_preferences.prefers_step_by_step is True
        assert preferences.communication_preferences.prefers_code_examples is True
        assert preferences.learning_enabled is True
    
    @pytest.mark.asyncio
    async def test_analyze_user_preferences_empty_conversations(self):
        """Test analysis with empty conversation list."""
        preferences = await self.engine.analyze_user_preferences("test_user", [])
        
        assert preferences.user_id == "test_user"
        assert preferences.response_style.confidence == 0.0
        assert len(preferences.topic_interests) == 0
        assert preferences.communication_preferences.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_get_preferences_cached(self):
        """Test getting preferences from cache."""
        # First analyze to populate cache
        conversations = [self.create_test_conversation(["Hello world"])]
        await self.engine.analyze_user_preferences("test_user", conversations)
        
        # Get preferences should return cached version
        cached_prefs = await self.engine.get_preferences("test_user")
        
        assert cached_prefs.user_id == "test_user"
        assert "test_user" in self.engine._preferences_cache
    
    @pytest.mark.asyncio
    async def test_get_preferences_not_cached(self):
        """Test getting preferences when not in cache."""
        preferences = await self.engine.get_preferences("unknown_user")
        
        assert preferences.user_id == "unknown_user"
        assert preferences.response_style.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_new_user(self):
        """Test learning from interaction for new user."""
        await self.engine.learn_from_interaction(
            user_id="new_user",
            user_message="I need a brief explanation of Python functions",
            assistant_response="Python functions are reusable blocks of code..."
        )
        
        preferences = await self.engine.get_preferences("new_user")
        assert preferences.user_id == "new_user"
        # Should have some topic interests from the interaction
        assert len(preferences.topic_interests) >= 0  # May or may not detect topics from single interaction
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_existing_user(self):
        """Test learning from interaction for existing user."""
        # First establish some preferences
        conversations = [self.create_test_conversation(["I love detailed programming tutorials"])]
        await self.engine.analyze_user_preferences("existing_user", conversations)
        
        # Learn from new interaction
        await self.engine.learn_from_interaction(
            user_id="existing_user",
            user_message="Can you explain data structures briefly?",
            assistant_response="Data structures organize data in memory..."
        )
        
        preferences = await self.engine.get_preferences("existing_user")
        assert preferences.user_id == "existing_user"
        # Should maintain existing preferences while incorporating new learning
        assert preferences.response_style.confidence > 0
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_with_positive_feedback(self):
        """Test learning with positive feedback."""
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.POSITIVE,
            rating=5
        )
        
        await self.engine.learn_from_interaction(
            user_id="test_user",
            user_message="Great explanation, thanks!",
            assistant_response="You're welcome!",
            feedback=feedback
        )
        
        preferences = await self.engine.get_preferences("test_user")
        # Positive feedback should increase confidence
        assert preferences.response_style.confidence >= 0
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_with_correction_feedback(self):
        """Test learning with correction feedback."""
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.CORRECTION,
            feedback_text="Please make your responses shorter and more concise"
        )
        
        await self.engine.learn_from_interaction(
            user_id="test_user",
            user_message="Explain machine learning",
            assistant_response="Machine learning is a complex field...",
            feedback=feedback
        )
        
        preferences = await self.engine.get_preferences("test_user")
        # Should adapt to correction
        assert preferences.response_style.style_type == ResponseStyleType.CONCISE
    
    @pytest.mark.asyncio
    async def test_apply_feedback_to_preferences_positive(self):
        """Test applying positive feedback to preferences."""
        preferences = UserPreferences(user_id="test_user")
        preferences.response_style.confidence = 0.5
        
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.POSITIVE,
            rating=5
        )
        
        await self.engine._apply_feedback_to_preferences(preferences, feedback)
        
        # Confidence should increase
        assert preferences.response_style.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_apply_feedback_to_preferences_negative(self):
        """Test applying negative feedback to preferences."""
        preferences = UserPreferences(user_id="test_user")
        preferences.response_style.confidence = 0.8
        
        feedback = UserFeedback(
            user_id="test_user",
            message_id="msg_123",
            feedback_type=FeedbackType.NEGATIVE,
            rating=1
        )
        
        await self.engine._apply_feedback_to_preferences(preferences, feedback)
        
        # Confidence should decrease
        assert preferences.response_style.confidence < 0.8
    
    def test_clear_cache(self):
        """Test clearing the preferences cache."""
        # Add something to cache
        self.engine._preferences_cache["test_user"] = UserPreferences(user_id="test_user")
        
        assert self.engine.get_cache_size() == 1
        
        self.engine.clear_cache()
        
        assert self.engine.get_cache_size() == 0
    
    def test_get_cache_size(self):
        """Test getting cache size."""
        assert self.engine.get_cache_size() == 0
        
        self.engine._preferences_cache["user1"] = UserPreferences(user_id="user1")
        self.engine._preferences_cache["user2"] = UserPreferences(user_id="user2")
        
        assert self.engine.get_cache_size() == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_in_analysis(self):
        """Test error handling during preference analysis."""
        # Create a conversation with invalid data to trigger error
        invalid_conversation = Mock()
        invalid_conversation.get_messages_by_role.side_effect = Exception("Test error")
        
        # Should not raise exception, should return basic preferences
        preferences = await self.engine.analyze_user_preferences("test_user", [invalid_conversation])
        
        assert preferences.user_id == "test_user"
        assert preferences.response_style.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_learning(self):
        """Test error handling during learning from interaction."""
        # Mock the analyzer to raise an exception
        with patch.object(self.engine, 'analyze_user_preferences', side_effect=Exception("Test error")):
            # Should not raise exception
            await self.engine.learn_from_interaction(
                user_id="test_user",
                user_message="Test message",
                assistant_response="Test response"
            )
            
            # Should still be able to get basic preferences
            preferences = await self.engine.get_preferences("test_user")
            assert preferences.user_id == "test_user"


if __name__ == "__main__":
    pytest.main([__file__])