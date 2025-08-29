"""
Unit tests for fallback mechanisms and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.memory.services.fallback_context_service import FallbackContextService
from src.memory.services.resilient_memory_service import ResilientMemoryService
from src.memory.utils.retry_mechanism import (
    RetryMechanism, RetryConfig, CircuitBreakerConfig, 
    CircuitBreakerState, execute_with_fallback, with_retry
)
from src.memory.models import (
    Conversation, Message, MessageRole, MessageExchange,
    ConversationContext, UserPreferences
)


class TestFallbackContextService:
    """Test cases for the fallback context service."""
    
    @pytest.fixture
    def fallback_service(self):
        """Create a fallback context service for testing."""
        return FallbackContextService()
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        messages = [
            Message(
                id="msg1",
                role=MessageRole.USER,
                content="Hello, I need help with Python",
                timestamp=datetime.now(timezone.utc)
            ),
            Message(
                id="msg2",
                role=MessageRole.ASSISTANT,
                content="I'd be happy to help you with Python!",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        return Conversation(
            id="conv1",
            user_id="user123",
            timestamp=datetime.now(timezone.utc),
            messages=messages
        )
    
    @pytest.mark.asyncio
    async def test_build_context_empty_cache(self, fallback_service):
        """Test building context when cache is empty."""
        context = await fallback_service.build_context("user123", "Hello")
        
        assert context.user_id == "user123"
        assert len(context.recent_messages) == 0
        assert len(context.relevant_history) == 0
        assert context.user_preferences is not None
        assert "New conversation" in context.context_summary
    
    @pytest.mark.asyncio
    async def test_build_context_with_cached_data(self, fallback_service):
        """Test building context with cached message data."""
        # Add some messages to cache first
        user_message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="Previous message",
            timestamp=datetime.now(timezone.utc)
        )
        assistant_message = Message(
            id="msg2",
            role=MessageRole.ASSISTANT,
            content="Previous response",
            timestamp=datetime.now(timezone.utc)
        )
        
        exchange = MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message
        )
        
        await fallback_service.update_context("user123", exchange)
        
        # Now build context
        context = await fallback_service.build_context("user123", "New message")
        
        assert context.user_id == "user123"
        assert len(context.recent_messages) == 2
        assert context.recent_messages[0].content == "Previous message"
        assert context.recent_messages[1].content == "Previous response"
        assert "Fallback mode" in context.context_summary
    
    @pytest.mark.asyncio
    async def test_summarize_conversation_empty(self, fallback_service, sample_conversation):
        """Test summarizing an empty conversation."""
        empty_conversation = Conversation(
            id="empty",
            user_id="user123",
            timestamp=datetime.now(timezone.utc),
            messages=[]
        )
        
        summary = await fallback_service.summarize_conversation(empty_conversation)
        
        assert summary.conversation_id == "empty"
        assert summary.summary_text == "Empty conversation"
        assert summary.message_count == 0
    
    @pytest.mark.asyncio
    async def test_summarize_conversation_with_messages(self, fallback_service, sample_conversation):
        """Test summarizing a conversation with messages."""
        summary = await fallback_service.summarize_conversation(sample_conversation)
        
        assert summary.conversation_id == "conv1"
        assert "Started with: Hello, I need help with Python" in summary.summary_text
        assert "Ended with: I'd be happy to help you with Python!" in summary.summary_text
        assert summary.message_count == 2
        assert len(summary.key_topics) > 0
    
    @pytest.mark.asyncio
    async def test_update_context_new_user(self, fallback_service):
        """Test updating context for a new user."""
        user_message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="First message",
            timestamp=datetime.now(timezone.utc)
        )
        assistant_message = Message(
            id="msg2",
            role=MessageRole.ASSISTANT,
            content="First response",
            timestamp=datetime.now(timezone.utc)
        )
        
        exchange = MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message
        )
        
        await fallback_service.update_context("newuser", exchange)
        
        # Check that user data was created
        assert "newuser" in fallback_service._basic_cache
        user_data = fallback_service._basic_cache["newuser"]
        assert len(user_data["recent_messages"]) == 2
        assert user_data["recent_messages"][0].content == "First message"
    
    @pytest.mark.asyncio
    async def test_update_context_message_limit(self, fallback_service):
        """Test that message limit is enforced."""
        # Add more messages than the limit
        for i in range(25):  # More than max_messages_per_user (20)
            user_message = Message(
                id=f"msg_user_{i}",
                role=MessageRole.USER,
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc)
            )
            assistant_message = Message(
                id=f"msg_assistant_{i}",
                role=MessageRole.ASSISTANT,
                content=f"Response {i}",
                timestamp=datetime.now(timezone.utc)
            )
            
            exchange = MessageExchange(
                user_message=user_message,
                assistant_message=assistant_message
            )
            
            await fallback_service.update_context("user123", exchange)
        
        # Check that only the last 20 messages are kept
        user_data = fallback_service._basic_cache["user123"]
        assert len(user_data["recent_messages"]) == 20
        # Should have the latest messages
        assert "Message 24" in user_data["recent_messages"][-2].content
    
    @pytest.mark.asyncio
    async def test_prune_old_context(self, fallback_service):
        """Test pruning old context data."""
        # Add user data with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=3)
        fallback_service._basic_cache["olduser"] = {
            "recent_messages": [],
            "last_updated": old_time
        }
        
        # Add user data with recent timestamp
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        fallback_service._basic_cache["recentuser"] = {
            "recent_messages": [],
            "last_updated": recent_time
        }
        
        await fallback_service.prune_old_context("olduser")
        await fallback_service.prune_old_context("recentuser")
        
        # Old user should be removed, recent user should remain
        assert "olduser" not in fallback_service._basic_cache
        assert "recentuser" in fallback_service._basic_cache
    
    @pytest.mark.asyncio
    async def test_get_relevant_history_returns_empty(self, fallback_service):
        """Test that get_relevant_history returns empty list in fallback mode."""
        history = await fallback_service.get_relevant_history("user123", "test message")
        assert history == []
    
    @pytest.mark.asyncio
    async def test_health_check(self, fallback_service):
        """Test health check functionality."""
        health = await fallback_service.health_check()
        
        assert health["service"] == "fallback_context_service"
        assert health["status"] == "healthy"
        assert health["mode"] == "fallback"
        assert "cache_size" in health
    
    def test_get_cache_stats(self, fallback_service):
        """Test getting cache statistics."""
        # Add some test data
        fallback_service._basic_cache["user1"] = {"recent_messages": [Mock(), Mock()]}
        fallback_service._basic_cache["user2"] = {"recent_messages": [Mock()]}
        
        stats = fallback_service.get_cache_stats()
        
        assert stats["cached_users"] == 2
        assert stats["total_cached_messages"] == 3
        assert stats["average_messages_per_user"] == 1.5
        assert "cache_utilization" in stats
    
    def test_extract_basic_topics(self, fallback_service):
        """Test basic topic extraction."""
        messages = [
            Message(
                id="msg1",
                role=MessageRole.USER,
                content="I need help with Python programming and debugging errors",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        topics = fallback_service._extract_basic_topics(messages)
        
        assert "programming" in topics
        assert "help" in topics
        assert "error" in topics


class TestRetryMechanism:
    """Test cases for the retry mechanism."""
    
    @pytest.fixture
    def retry_config(self):
        """Create a retry configuration for testing."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Short delay for testing
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable testing
            retryable_exceptions=[ConnectionError, TimeoutError]
        )
    
    @pytest.fixture
    def retry_mechanism(self, retry_config):
        """Create a retry mechanism for testing."""
        return RetryMechanism(retry_config)
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self, retry_mechanism):
        """Test successful execution on first attempt."""
        async def success_func():
            return "success"
        
        result = await retry_mechanism.execute_with_retry(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_failures(self, retry_mechanism):
        """Test successful execution after some failures."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await retry_mechanism.execute_with_retry(flaky_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_all_attempts_fail(self, retry_mechanism):
        """Test when all retry attempts fail."""
        async def always_fail():
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            await retry_mechanism.execute_with_retry(always_fail)
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_exception(self, retry_mechanism):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        async def non_retryable_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError, match="Non-retryable error"):
            await retry_mechanism.execute_with_retry(non_retryable_fail)
        
        assert call_count == 1  # Should not retry
    
    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        breaker = CircuitBreakerState(config)
        
        # Initial state should be CLOSED
        assert breaker.state == "CLOSED"
        assert breaker.can_attempt() is True
        
        # Record failures to reach threshold
        breaker.record_failure()
        assert breaker.state == "CLOSED"
        assert breaker.can_attempt() is True
        
        breaker.record_failure()
        assert breaker.state == "OPEN"
        assert breaker.can_attempt() is False
        
        # Record success should reset
        breaker.record_success()
        assert breaker.state == "CLOSED"
        assert breaker.can_attempt() is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, retry_mechanism):
        """Test circuit breaker integration with retry mechanism."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Service unavailable")
        
        # First call should fail and open circuit breaker
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(
                failing_func,
                circuit_breaker_key="test_service",
                circuit_breaker_config=CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60.0)
            )
        
        # Second call should be blocked by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker test_service is OPEN"):
            await retry_mechanism.execute_with_retry(
                failing_func,
                circuit_breaker_key="test_service"
            )
        
        # Reset circuit breaker
        retry_mechanism.reset_circuit_breaker("test_service")
        
        # Should be able to attempt again
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(
                failing_func,
                circuit_breaker_key="test_service"
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self):
        """Test execute_with_fallback when primary succeeds."""
        async def primary():
            return "primary_result"
        
        async def fallback():
            return "fallback_result"
        
        result = await execute_with_fallback(primary, fallback)
        assert result == "primary_result"
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_fails(self):
        """Test execute_with_fallback when primary fails."""
        async def primary():
            raise ConnectionError("Primary failed")
        
        async def fallback():
            return "fallback_result"
        
        result = await execute_with_fallback(primary, fallback, retry_primary=False)
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test the with_retry decorator."""
        call_count = 0
        
        @with_retry(max_attempts=3, base_delay=0.1, retryable_exceptions=[ValueError])
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await decorated_func()
        assert result == "success"
        assert call_count == 3


class TestResilientMemoryService:
    """Test cases for the resilient memory service."""
    
    @pytest.fixture
    def mock_primary_service(self):
        """Create a mock primary memory service."""
        service = Mock()
        service.initialize = AsyncMock()
        service.store_conversation = AsyncMock()
        service.retrieve_context = AsyncMock()
        service.search_history = AsyncMock(return_value=[])
        service.delete_user_data = AsyncMock()
        service.export_user_data = AsyncMock()
        service.update_privacy_settings = AsyncMock()
        service.get_privacy_settings = AsyncMock()
        service.health_check = AsyncMock(return_value={"status": "healthy"})
        return service
    
    @pytest.fixture
    def resilient_service(self, mock_primary_service):
        """Create a resilient memory service for testing."""
        return ResilientMemoryService(primary_service=mock_primary_service)
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, resilient_service, mock_primary_service):
        """Test successful initialization."""
        await resilient_service.initialize()
        
        assert resilient_service._initialized is True
        assert resilient_service._service_health['primary_service'] is True
        assert resilient_service._degraded_mode is False
        mock_primary_service.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_primary_fails(self, mock_primary_service):
        """Test initialization when primary service fails."""
        mock_primary_service.initialize.side_effect = ConnectionError("Database unavailable")
        
        resilient_service = ResilientMemoryService(primary_service=mock_primary_service)
        await resilient_service.initialize()
        
        assert resilient_service._initialized is True
        assert resilient_service._service_health['primary_service'] is False
        assert resilient_service._degraded_mode is True
    
    @pytest.mark.asyncio
    async def test_store_conversation_success(self, resilient_service, mock_primary_service):
        """Test successful conversation storage."""
        await resilient_service.initialize()
        
        conversation = Mock()
        conversation.id = "conv123"
        conversation.messages = []
        
        await resilient_service.store_conversation("user123", conversation)
        
        mock_primary_service.store_conversation.assert_called_once_with("user123", conversation)
    
    @pytest.mark.asyncio
    async def test_store_conversation_fallback(self, resilient_service, mock_primary_service):
        """Test conversation storage fallback when primary fails."""
        from datetime import datetime, timezone
        from src.memory.models import Message, MessageRole
        
        await resilient_service.initialize()
        
        # Make primary service fail
        mock_primary_service.store_conversation.side_effect = ConnectionError("Storage failed")
        
        # Create proper Message objects instead of Mock
        user_msg = Message(
            role=MessageRole.USER,
            content="Test user message",
            timestamp=datetime.now(timezone.utc)
        )
        assistant_msg = Message(
            role=MessageRole.ASSISTANT,
            content="Test assistant message",
            timestamp=datetime.now(timezone.utc)
        )
        
        conversation = Mock()
        conversation.id = "conv123"
        conversation.messages = [user_msg, assistant_msg]
        
        # Should not raise exception, should use fallback
        await resilient_service.store_conversation("user123", conversation)
        
        # Primary should have been attempted 3 times due to retry mechanism
        assert mock_primary_service.store_conversation.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retrieve_context_success(self, resilient_service, mock_primary_service):
        """Test successful context retrieval."""
        await resilient_service.initialize()
        
        expected_context = Mock()
        mock_primary_service.retrieve_context.return_value = expected_context
        
        result = await resilient_service.retrieve_context("user123")
        
        assert result == expected_context
        mock_primary_service.retrieve_context.assert_called_once_with("user123", None)
    
    @pytest.mark.asyncio
    async def test_retrieve_context_fallback(self, resilient_service, mock_primary_service):
        """Test context retrieval fallback when primary fails."""
        await resilient_service.initialize()
        
        # Make primary service fail
        mock_primary_service.retrieve_context.side_effect = ConnectionError("Context failed")
        
        result = await resilient_service.retrieve_context("user123")
        
        # Should return a context (from fallback service)
        assert result is not None
        assert result.user_id == "user123"
        # Should be called 3 times due to retry mechanism
        assert mock_primary_service.retrieve_context.call_count == 3
    
    @pytest.mark.asyncio
    async def test_search_history_degraded_mode(self, resilient_service):
        """Test search history in degraded mode."""
        # Force degraded mode
        await resilient_service.force_degraded_mode(True)
        await resilient_service.initialize()
        
        query = Mock()
        result = await resilient_service.search_history("user123", query)
        
        # Should return empty list in degraded mode
        assert result == []
    
    @pytest.mark.asyncio
    async def test_health_check(self, resilient_service, mock_primary_service):
        """Test comprehensive health check."""
        await resilient_service.initialize()
        
        health = await resilient_service.health_check()
        
        assert health["service"] == "resilient_memory_service"
        assert health["initialized"] is True
        assert "service_health" in health
        assert "circuit_breakers" in health
        assert "fallback_services" in health
    
    @pytest.mark.asyncio
    async def test_recover_service(self, resilient_service, mock_primary_service):
        """Test service recovery functionality."""
        await resilient_service.initialize()
        
        # Simulate service failure
        resilient_service._service_health['primary_service'] = False
        resilient_service._degraded_mode = True
        
        # Attempt recovery
        success = await resilient_service.recover_service('primary_service')
        
        assert success is True
        assert resilient_service._service_health['primary_service'] is True
        assert resilient_service._degraded_mode is False
    
    def test_get_service_metrics(self, resilient_service):
        """Test getting service metrics."""
        metrics = resilient_service.get_service_metrics()
        
        assert "service_health" in metrics
        assert "degraded_mode" in metrics
        assert "circuit_breaker_status" in metrics
        assert "fallback_cache_stats" in metrics
    
    @pytest.mark.asyncio
    async def test_force_degraded_mode(self, resilient_service):
        """Test forcing degraded mode."""
        await resilient_service.force_degraded_mode(True)
        assert resilient_service._degraded_mode is True
        
        await resilient_service.force_degraded_mode(False)
        assert resilient_service._degraded_mode is False


if __name__ == "__main__":
    pytest.main([__file__])