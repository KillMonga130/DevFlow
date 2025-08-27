"""
Unit tests for the ContextManager service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from src.memory.services.context_manager import ContextManager
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationSummary,
    ConversationContext, MessageExchange, UserPreferences
)


class TestContextManager:
    """Test cases for ContextManager."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage layer."""
        storage = AsyncMock()
        return storage
    
    @pytest.fixture
    def context_manager(self, mock_storage):
        """Create a ContextManager instance with mock storage."""
        return ContextManager(storage_layer=mock_storage)
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        messages = [
            Message(role=MessageRole.USER, content="Hello, I need help with Python"),
            Message(role=MessageRole.ASSISTANT, content="I'd be happy to help with Python! What specific topic?"),
            Message(role=MessageRole.USER, content="I want to learn about data structures"),
            Message(role=MessageRole.ASSISTANT, content="Great! Let's start with lists and dictionaries...")
        ]
        
        conversation = Conversation(
            id="conv-123",
            user_id="user-456",
            messages=messages,
            timestamp=datetime.now(timezone.utc)
        )
        return conversation
    
    @pytest.fixture
    def sample_summaries(self):
        """Create sample conversation summaries."""
        return [
            ConversationSummary(
                conversation_id="conv-1",
                timestamp=datetime.now(timezone.utc) - timedelta(days=1),
                summary_text="Discussion about Python basics and syntax",
                key_topics=["python", "syntax", "basics"],
                importance_score=0.8,
                message_count=10
            ),
            ConversationSummary(
                conversation_id="conv-2", 
                timestamp=datetime.now(timezone.utc) - timedelta(days=3),
                summary_text="Help with data structures and algorithms",
                key_topics=["data", "structures", "algorithms"],
                importance_score=0.9,
                message_count=15
            )
        ]
    
    @pytest.mark.asyncio
    async def test_build_context_success(self, context_manager, mock_storage, sample_conversation):
        """Test successful context building."""
        # Setup mock responses
        mock_storage.get_user_conversations.return_value = [sample_conversation]
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_conversation_summaries.return_value = []
        
        # Build context
        context = await context_manager.build_context("user-456", "Tell me about lists")
        
        # Assertions
        assert isinstance(context, ConversationContext)
        assert context.user_id == "user-456"
        assert len(context.recent_messages) > 0
        assert context.context_summary is not None
        assert context.context_timestamp is not None
    
    @pytest.mark.asyncio
    async def test_build_context_with_cache(self, context_manager, mock_storage):
        """Test context building uses cache when available."""
        # First call
        mock_storage.get_user_conversations.return_value = []
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_conversation_summaries.return_value = []
        
        context1 = await context_manager.build_context("user-456", "Hello")
        
        # Second call should use cache
        context2 = await context_manager.build_context("user-456", "Hello again")
        
        # Should only call storage once
        assert mock_storage.get_user_conversations.call_count == 1
        assert context1.user_id == context2.user_id
    
    @pytest.mark.asyncio
    async def test_build_context_error_handling(self, context_manager, mock_storage):
        """Test context building handles errors gracefully."""
        # Setup mock to raise exception
        mock_storage.get_user_conversations.side_effect = Exception("Database error")
        
        # Build context should not raise exception
        context = await context_manager.build_context("user-456", "Hello")
        
        # Should return minimal context
        assert isinstance(context, ConversationContext)
        assert context.user_id == "user-456"
        assert "Error retrieving context" in context.context_summary
    
    @pytest.mark.asyncio
    async def test_summarize_conversation_success(self, context_manager, sample_conversation):
        """Test successful conversation summarization."""
        summary = await context_manager.summarize_conversation(sample_conversation)
        
        # Assertions
        assert isinstance(summary, ConversationSummary)
        assert summary.conversation_id == sample_conversation.id
        assert summary.message_count == len(sample_conversation.messages)
        assert len(summary.key_topics) > 0
        assert summary.importance_score > 0
        assert "Python" in summary.summary_text or "python" in summary.key_topics
    
    @pytest.mark.asyncio
    async def test_summarize_empty_conversation(self, context_manager):
        """Test summarization of empty conversation."""
        empty_conversation = Conversation(
            id="empty-conv",
            user_id="user-456",
            messages=[],
            timestamp=datetime.now(timezone.utc)
        )
        
        summary = await context_manager.summarize_conversation(empty_conversation)
        
        assert summary.message_count == 0
        assert summary.summary_text == "Empty conversation"
        assert len(summary.key_topics) == 0
    
    @pytest.mark.asyncio
    async def test_update_context_with_cache(self, context_manager, mock_storage):
        """Test context update with cached context."""
        # First build context to populate cache
        mock_storage.get_user_conversations.return_value = []
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_conversation_summaries.return_value = []
        
        await context_manager.build_context("user-456", "Hello")
        
        # Create message exchange
        user_msg = Message(role=MessageRole.USER, content="New question")
        assistant_msg = Message(role=MessageRole.ASSISTANT, content="New answer")
        exchange = MessageExchange(user_message=user_msg, assistant_message=assistant_msg)
        
        # Update context
        await context_manager.update_context("user-456", exchange)
        
        # Verify cache was updated
        cached_context = context_manager._context_cache["user-456"]
        assert len(cached_context.recent_messages) >= 2  # Should have both messages
    
    @pytest.mark.asyncio
    async def test_update_context_error_handling(self, context_manager):
        """Test context update handles errors gracefully."""
        # Create invalid exchange
        exchange = MessageExchange(
            user_message=Message(role=MessageRole.USER, content="Test"),
            assistant_message=Message(role=MessageRole.ASSISTANT, content="Response")
        )
        
        # Should not raise exception even with no cached context
        await context_manager.update_context("nonexistent-user", exchange)
    
    @pytest.mark.asyncio
    async def test_prune_old_context(self, context_manager, mock_storage):
        """Test pruning of old context data."""
        # Add old context to cache
        old_context = ConversationContext(
            user_id="user-456",
            context_timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        context_manager._context_cache["user-456"] = old_context
        
        # Setup mock for storage
        mock_storage.get_conversation_summaries.return_value = []
        
        # Prune context
        await context_manager.prune_old_context("user-456")
        
        # Old context should be removed from cache
        assert "user-456" not in context_manager._context_cache
    
    @pytest.mark.asyncio
    async def test_get_relevant_history_success(self, context_manager, mock_storage, sample_summaries):
        """Test getting relevant historical context."""
        mock_storage.get_conversation_summaries.return_value = sample_summaries
        
        relevant = await context_manager.get_relevant_history(
            "user-456", 
            "I need help with Python data structures", 
            limit=2
        )
        
        # Should return summaries ordered by relevance
        assert len(relevant) <= 2
        assert all(isinstance(s, ConversationSummary) for s in relevant)
        
        # More relevant summary should be first (data structures)
        if len(relevant) > 1:
            assert "data" in relevant[0].key_topics or "structures" in relevant[0].key_topics
    
    @pytest.mark.asyncio
    async def test_get_relevant_history_empty(self, context_manager, mock_storage):
        """Test getting relevant history with no summaries."""
        mock_storage.get_conversation_summaries.return_value = []
        
        relevant = await context_manager.get_relevant_history("user-456", "Hello")
        
        assert len(relevant) == 0
    
    def test_extract_key_topics(self, context_manager):
        """Test key topic extraction from messages."""
        messages = [
            Message(role=MessageRole.USER, content="I want to learn Python programming"),
            Message(role=MessageRole.USER, content="Specifically about data structures and algorithms"),
            Message(role=MessageRole.ASSISTANT, content="Great choice! Python is excellent for learning.")
        ]
        
        topics = context_manager._extract_key_topics(messages)
        
        assert isinstance(topics, list)
        assert len(topics) > 0
        # Should extract meaningful topics
        topic_text = " ".join(topics).lower()
        assert any(word in topic_text for word in ["python", "data", "structures", "algorithms", "learn"])
    
    def test_extract_keywords(self, context_manager):
        """Test keyword extraction from text."""
        text = "I want to learn Python programming and data structures"
        
        keywords = context_manager._extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert "python" in keywords
        assert "programming" in keywords
        assert "data" in keywords
        assert "structures" in keywords
        # Should not include stop words
        assert "want" not in keywords
        assert "and" not in keywords
    
    def test_calculate_importance_score(self, context_manager, sample_conversation):
        """Test importance score calculation."""
        score = context_manager._calculate_importance_score(sample_conversation)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should have some importance
    
    def test_calculate_relevance_score(self, context_manager):
        """Test relevance score calculation."""
        current_keywords = ["python", "programming", "data"]
        summary_topics = ["python", "data", "structures"]
        summary_text = "Discussion about Python data structures and programming concepts"
        
        score = context_manager._calculate_relevance_score(
            current_keywords, summary_topics, summary_text
        )
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should have some relevance
    
    def test_generate_context_summary(self, context_manager):
        """Test context summary generation."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!")
        ]
        
        summaries = [
            ConversationSummary(
                conversation_id="conv-1",
                timestamp=datetime.now(timezone.utc),
                summary_text="Previous discussion",
                key_topics=["greeting"],
                importance_score=0.5,
                message_count=2
            )
        ]
        
        context_summary = context_manager._generate_context_summary(messages, summaries)
        
        assert isinstance(context_summary, str)
        assert len(context_summary) > 0
        assert "Recent context" in context_summary
        assert "Relevant history" in context_summary
    
    def test_analyze_conversation_flow(self, context_manager):
        """Test conversation flow analysis."""
        # Test help-seeking conversation
        help_messages = [
            Message(role=MessageRole.USER, content="I need help with Python"),
            Message(role=MessageRole.ASSISTANT, content="I can help with that"),
            Message(role=MessageRole.USER, content="How do I create a list?"),
            Message(role=MessageRole.ASSISTANT, content="You can use square brackets")
        ]
        
        flow = context_manager._analyze_conversation_flow(help_messages)
        assert flow == "Help-seeking conversation"
        
        # Test problem-solving conversation
        problem_messages = [
            Message(role=MessageRole.USER, content="I have a problem with my code"),
            Message(role=MessageRole.ASSISTANT, content="Let me help you debug it"),
            Message(role=MessageRole.USER, content="The error keeps happening"),
            Message(role=MessageRole.ASSISTANT, content="Let's check the stack trace")
        ]
        
        flow = context_manager._analyze_conversation_flow(problem_messages)
        assert flow == "Problem-solving discussion"
    
    def test_extract_key_exchanges(self, context_manager):
        """Test key exchange extraction."""
        user_messages = [
            Message(role=MessageRole.USER, content="How do I implement a binary search algorithm?"),
            Message(role=MessageRole.USER, content="What is the time complexity?")
        ]
        
        assistant_messages = [
            Message(role=MessageRole.ASSISTANT, content="Binary search works by repeatedly dividing the search space in half..."),
            Message(role=MessageRole.ASSISTANT, content="The time complexity is O(log n)")
        ]
        
        # Set timestamps to ensure proper ordering
        base_time = datetime.now(timezone.utc)
        user_messages[0].timestamp = base_time
        assistant_messages[0].timestamp = base_time + timedelta(seconds=1)
        user_messages[1].timestamp = base_time + timedelta(seconds=2)
        assistant_messages[1].timestamp = base_time + timedelta(seconds=3)
        
        exchanges = context_manager._extract_key_exchanges(user_messages, assistant_messages)
        
        assert isinstance(exchanges, list)
        assert len(exchanges) <= 2  # Should extract top 2 exchanges
        if exchanges:
            assert "Q:" in exchanges[0] and "A:" in exchanges[0]
    
    def test_calculate_message_importance(self, context_manager):
        """Test message importance calculation."""
        # High importance message
        important_msg = Message(
            role=MessageRole.USER, 
            content="How do I debug this critical error in my production code? It's urgent and affecting users."
        )
        
        importance = context_manager._calculate_message_importance(important_msg)
        assert isinstance(importance, float)
        assert 0.0 <= importance <= 1.0
        assert importance > 0.5  # Should be high importance
        
        # Low importance message
        simple_msg = Message(role=MessageRole.USER, content="Hi")
        simple_importance = context_manager._calculate_message_importance(simple_msg)
        assert simple_importance < importance
    
    def test_identify_conversation_outcome(self, context_manager):
        """Test conversation outcome identification."""
        # Successful resolution
        success_messages = [
            Message(role=MessageRole.USER, content="I have a problem"),
            Message(role=MessageRole.ASSISTANT, content="Let me help you"),
            Message(role=MessageRole.USER, content="Thanks! That worked perfectly!")
        ]
        
        outcome = context_manager._identify_conversation_outcome(success_messages)
        assert outcome == "Successfully resolved"
        
        # Unresolved issue
        unresolved_messages = [
            Message(role=MessageRole.USER, content="I have a problem"),
            Message(role=MessageRole.ASSISTANT, content="Try this solution"),
            Message(role=MessageRole.USER, content="Still not working, I'm still confused")
        ]
        
        outcome = context_manager._identify_conversation_outcome(unresolved_messages)
        assert outcome == "Unresolved issues remain"
    
    def test_analyze_message_context(self, context_manager):
        """Test message context analysis."""
        message = "How do I implement a binary search algorithm in Python? I need help with the recursive approach."
        
        analysis = context_manager._analyze_message_context(message)
        
        assert isinstance(analysis, dict)
        assert 'keywords' in analysis
        assert 'intent' in analysis
        assert 'topics' in analysis
        assert 'complexity' in analysis
        assert 'question_type' in analysis
        assert 'urgency' in analysis
        
        # Check specific analysis results
        assert analysis['intent'] == 'question'
        assert analysis['question_type'] == 'procedural'
        assert 'programming' in analysis['topics'] or 'algorithms' in analysis['topics']
    
    def test_classify_message_intent(self, context_manager):
        """Test message intent classification."""
        test_cases = [
            ("How do I do this?", "question"),
            ("I need help with Python", "help_request"),
            ("I have an error in my code", "problem_report"),
            ("Can you explain how this works?", "learning"),
            ("Thank you for your help!", "gratitude"),
            ("This is a statement", "statement")
        ]
        
        for message, expected_intent in test_cases:
            intent = context_manager._classify_message_intent(message)
            assert intent == expected_intent
    
    def test_calculate_semantic_relevance(self, context_manager):
        """Test semantic relevance calculation."""
        current_analysis = {
            'keywords': ['python', 'programming', 'data', 'structures'],
            'topics': ['programming', 'data_structures']
        }
        
        summary = ConversationSummary(
            conversation_id="conv-1",
            timestamp=datetime.now(timezone.utc),
            summary_text="Discussion about Python data structures and programming concepts",
            key_topics=["python", "data_structures", "programming"],
            importance_score=0.8,
            message_count=10
        )
        
        relevance = context_manager._calculate_semantic_relevance(current_analysis, summary)
        
        assert isinstance(relevance, float)
        assert 0.0 <= relevance <= 1.0
        assert relevance > 0.5  # Should be highly relevant
    
    def test_ensure_topic_diversity(self, context_manager):
        """Test topic diversity in summary selection."""
        summaries = [
            (ConversationSummary(
                conversation_id="conv-1",
                timestamp=datetime.now(timezone.utc),
                summary_text="Python discussion",
                key_topics=["python", "programming"],
                importance_score=0.9,
                message_count=10
            ), 0.9, {}),
            (ConversationSummary(
                conversation_id="conv-2",
                timestamp=datetime.now(timezone.utc),
                summary_text="Another Python discussion",
                key_topics=["python", "coding"],
                importance_score=0.8,
                message_count=8
            ), 0.8, {}),
            (ConversationSummary(
                conversation_id="conv-3",
                timestamp=datetime.now(timezone.utc),
                summary_text="JavaScript discussion",
                key_topics=["javascript", "web"],
                importance_score=0.7,
                message_count=6
            ), 0.7, {})
        ]
        
        diverse = context_manager._ensure_topic_diversity(summaries, limit=2)
        
        assert len(diverse) <= 2
        # Should prefer diverse topics over similar ones
        if len(diverse) == 2:
            topics1 = set(diverse[0][0].key_topics)
            topics2 = set(diverse[1][0].key_topics)
            # Should have some topic diversity
            assert len(topics1 & topics2) < len(topics1) or len(topics1 & topics2) < len(topics2)


class TestContextManagerIntegration:
    """Integration tests for ContextManager."""
    
    @pytest.mark.asyncio
    async def test_full_context_workflow(self):
        """Test complete context management workflow."""
        # This would require actual storage layer integration
        # For now, we'll test with mocked storage
        
        mock_storage = AsyncMock()
        context_manager = ContextManager(storage_layer=mock_storage)
        
        # Setup mock data
        conversation = Conversation(
            id="conv-123",
            user_id="user-456",
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!")
            ]
        )
        
        mock_storage.get_user_conversations.return_value = [conversation]
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_conversation_summaries.return_value = []
        
        # Test workflow
        context = await context_manager.build_context("user-456", "How are you?")
        assert context.user_id == "user-456"
        
        # Test summarization
        summary = await context_manager.summarize_conversation(conversation)
        assert summary.conversation_id == conversation.id
        
        # Test context update
        exchange = MessageExchange(
            user_message=Message(role=MessageRole.USER, content="New message"),
            assistant_message=Message(role=MessageRole.ASSISTANT, content="New response")
        )
        await context_manager.update_context("user-456", exchange)
        
        # Test pruning
        await context_manager.prune_old_context("user-456")
    
    @pytest.mark.asyncio
    async def test_context_retrieval_integration(self):
        """Test context retrieval with realistic data."""
        mock_storage = AsyncMock()
        context_manager = ContextManager(storage_layer=mock_storage)
        
        # Create realistic conversation history
        conversations = [
            Conversation(
                id="conv-1",
                user_id="user-123",
                messages=[
                    Message(role=MessageRole.USER, content="How do I implement a binary search?"),
                    Message(role=MessageRole.ASSISTANT, content="Binary search works by dividing the search space..."),
                    Message(role=MessageRole.USER, content="What's the time complexity?"),
                    Message(role=MessageRole.ASSISTANT, content="The time complexity is O(log n)")
                ],
                timestamp=datetime.now(timezone.utc) - timedelta(days=1)
            ),
            Conversation(
                id="conv-2", 
                user_id="user-123",
                messages=[
                    Message(role=MessageRole.USER, content="I need help with sorting algorithms"),
                    Message(role=MessageRole.ASSISTANT, content="There are several sorting algorithms..."),
                    Message(role=MessageRole.USER, content="Which one is fastest?"),
                    Message(role=MessageRole.ASSISTANT, content="It depends on the data size and characteristics")
                ],
                timestamp=datetime.now(timezone.utc) - timedelta(days=2)
            )
        ]
        
        # Create conversation summaries
        summaries = []
        for conv in conversations:
            summary = await context_manager.summarize_conversation(conv)
            summaries.append(summary)
        
        # Setup mock responses
        mock_storage.get_user_conversations.return_value = conversations
        mock_storage.get_conversation_summaries.return_value = summaries
        mock_storage.get_user_preferences.return_value = None
        
        # Test context building for algorithm-related query
        context = await context_manager.build_context("user-123", "How do I implement quicksort?")
        
        # Verify context contains relevant information
        assert context.user_id == "user-123"
        assert len(context.recent_messages) > 0
        assert len(context.relevant_history) > 0
        assert "algorithm" in context.context_summary.lower() or "sort" in context.context_summary.lower()
        
        # Test relevance scoring
        relevant_history = await context_manager.get_relevant_history(
            "user-123", 
            "What's the best sorting algorithm for large datasets?",
            limit=3
        )
        
        assert len(relevant_history) > 0
        # Should prioritize sorting-related conversation
        assert any("sort" in summary.summary_text.lower() for summary in relevant_history)
    
    @pytest.mark.asyncio
    async def test_conversation_specific_context(self):
        """Test getting context for a specific conversation."""
        mock_storage = AsyncMock()
        context_manager = ContextManager(storage_layer=mock_storage)
        
        # Create a conversation in progress
        current_conversation = Conversation(
            id="conv-current",
            user_id="user-789",
            messages=[
                Message(role=MessageRole.USER, content="I'm working on a Python project"),
                Message(role=MessageRole.ASSISTANT, content="That's great! What kind of project?"),
                Message(role=MessageRole.USER, content="A web scraper using BeautifulSoup"),
                Message(role=MessageRole.ASSISTANT, content="BeautifulSoup is excellent for web scraping...")
            ],
            timestamp=datetime.now(timezone.utc)
        )
        
        # Create historical summaries
        historical_summaries = [
            ConversationSummary(
                conversation_id="conv-old-1",
                timestamp=datetime.now(timezone.utc) - timedelta(days=3),
                summary_text="Discussion about Python web scraping and requests library",
                key_topics=["python", "web", "scraping", "requests"],
                importance_score=0.8,
                message_count=12
            ),
            ConversationSummary(
                conversation_id="conv-old-2",
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                summary_text="Help with JavaScript and DOM manipulation",
                key_topics=["javascript", "dom", "web"],
                importance_score=0.6,
                message_count=8
            )
        ]
        
        # Setup mock responses
        mock_storage.get_conversation.return_value = current_conversation
        mock_storage.get_conversation_summaries.return_value = historical_summaries
        mock_storage.get_user_preferences.return_value = None
        
        # Test getting context for the current conversation
        context = await context_manager.get_context_for_conversation("user-789", "conv-current")
        
        # Verify context
        assert context.user_id == "user-789"
        assert len(context.recent_messages) == 4  # All messages from current conversation
        assert len(context.relevant_history) > 0
        
        # Should prioritize Python/scraping related history
        relevant_summary = context.relevant_history[0]
        assert "python" in relevant_summary.key_topics or "scraping" in relevant_summary.key_topics
        
        # Should exclude current conversation from history
        assert all(s.conversation_id != "conv-current" for s in context.relevant_history)
    
    @pytest.mark.asyncio
    async def test_context_statistics(self):
        """Test context statistics generation."""
        mock_storage = AsyncMock()
        context_manager = ContextManager(storage_layer=mock_storage)
        
        # Create mock summaries with various topics
        summaries = [
            ConversationSummary(
                conversation_id=f"conv-{i}",
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                summary_text=f"Conversation {i}",
                key_topics=["python", "programming"] if i % 2 == 0 else ["javascript", "web"],
                importance_score=0.7,
                message_count=10 + i
            )
            for i in range(10)
        ]
        
        conversations = [
            Conversation(
                id=f"conv-{i}",
                user_id="user-stats",
                messages=[Message(role=MessageRole.USER, content=f"Message {i}")],
                timestamp=datetime.now(timezone.utc) - timedelta(days=i)
            )
            for i in range(5)
        ]
        
        mock_storage.get_conversation_summaries.return_value = summaries
        mock_storage.get_user_conversations.return_value = conversations
        
        # Test statistics generation
        stats = await context_manager.get_context_statistics("user-stats")
        
        # Verify statistics
        assert stats['total_conversations'] == 10
        assert stats['recent_conversations'] == 5
        assert stats['total_messages'] > 0
        assert stats['average_messages_per_conversation'] > 0
        assert len(stats['most_common_topics']) > 0
        assert 'python' in [topic['topic'] for topic in stats['most_common_topics']]
        assert isinstance(stats['context_cache_status'], bool)
    
    @pytest.mark.asyncio
    async def test_context_cache_management(self):
        """Test context cache refresh and management."""
        mock_storage = AsyncMock()
        context_manager = ContextManager(storage_layer=mock_storage)
        
        # Setup basic mock responses
        mock_storage.get_user_conversations.return_value = []
        mock_storage.get_conversation_summaries.return_value = []
        mock_storage.get_user_preferences.return_value = None
        
        # Build context to populate cache
        await context_manager.build_context("user-cache", "Hello")
        assert "user-cache" in context_manager._context_cache
        
        # Test cache refresh
        await context_manager.refresh_context_cache("user-cache")
        assert "user-cache" not in context_manager._context_cache
        
        # Test cache refresh for non-existent user (should not error)
        await context_manager.refresh_context_cache("non-existent-user")