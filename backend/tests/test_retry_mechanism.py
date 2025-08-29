"""
Unit tests for retry mechanism utilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from src.memory.utils.retry_mechanism import (
    RetryConfig, CircuitBreakerConfig, CircuitBreakerState,
    RetryMechanism, with_retry, execute_with_fallback,
    default_retry_mechanism
)


class TestRetryConfig:
    """Test cases for RetryConfig class."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        custom_exceptions = [ValueError, TypeError]
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False,
            retryable_exceptions=custom_exceptions
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.retryable_exceptions == custom_exceptions


class TestCircuitBreakerConfig:
    """Test cases for CircuitBreakerConfig class."""
    
    def test_default_config(self):
        """Test default circuit breaker configuration."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == Exception
    
    def test_custom_config(self):
        """Test custom circuit breaker configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=ConnectionError
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.expected_exception == ConnectionError


class TestCircuitBreakerState:
    """Test cases for CircuitBreakerState class."""
    
    @pytest.fixture
    def circuit_breaker_config(self):
        """Create a circuit breaker config for testing."""
        return CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
    
    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Create a circuit breaker state for testing."""
        return CircuitBreakerState(circuit_breaker_config)
    
    def test_initial_state(self, circuit_breaker):
        """Test initial circuit breaker state."""
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.last_failure_time is None
        assert circuit_breaker.can_attempt() is True
    
    def test_record_success(self, circuit_breaker):
        """Test recording successful operations."""
        # First record some failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        assert circuit_breaker.failure_count == 2
        
        # Record success should reset
        circuit_breaker.record_success()
        
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "CLOSED"
    
    def test_record_failure_threshold(self, circuit_breaker):
        """Test recording failures up to threshold."""
        # Record failures below threshold
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "CLOSED"
        assert circuit_breaker.failure_count == 2
        
        # Record failure that hits threshold
        circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "OPEN"
        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.last_failure_time is not None
    
    def test_can_attempt_open_state(self, circuit_breaker):
        """Test can_attempt when circuit breaker is open."""
        # Force circuit breaker to open state
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "OPEN"
        assert circuit_breaker.can_attempt() is False
    
    def test_recovery_timeout(self, circuit_breaker):
        """Test recovery timeout behavior."""
        # Force circuit breaker to open state
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "OPEN"
        
        # Simulate time passing (mock the datetime)
        future_time = datetime.now() + timedelta(seconds=10)
        with patch('src.memory.utils.retry_mechanism.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time
            
            # Should transition to HALF_OPEN
            assert circuit_breaker.can_attempt() is True
            assert circuit_breaker.state == "HALF_OPEN"
    
    def test_half_open_state(self, circuit_breaker):
        """Test half-open state behavior."""
        # Force to half-open state
        circuit_breaker.state = "HALF_OPEN"
        
        assert circuit_breaker.can_attempt() is True


class TestRetryMechanism:
    """Test cases for RetryMechanism class."""
    
    @pytest.fixture
    def retry_config(self):
        """Create a retry config for testing."""
        return RetryConfig(max_attempts=3, base_delay=0.1, jitter=False)
    
    @pytest.fixture
    def retry_mechanism(self, retry_config):
        """Create a retry mechanism for testing."""
        return RetryMechanism(retry_config)
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, retry_mechanism):
        """Test successful function execution without retries."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_mechanism.execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_retry_on_retryable_exception(self, retry_mechanism):
        """Test retry behavior on retryable exceptions."""
        mock_func = AsyncMock(side_effect=[ConnectionError("Connection failed"), "success"])
        
        result = await retry_mechanism.execute_with_retry(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self, retry_mechanism):
        """Test behavior when max attempts are exceeded."""
        mock_func = AsyncMock(side_effect=ConnectionError("Persistent failure"))
        
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 3  # max_attempts
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, retry_mechanism):
        """Test that non-retryable exceptions are not retried."""
        mock_func = AsyncMock(side_effect=ValueError("Invalid value"))
        
        with pytest.raises(ValueError):
            await retry_mechanism.execute_with_retry(mock_func)
        
        assert mock_func.call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_sync_function_execution(self, retry_mechanism):
        """Test execution of synchronous functions."""
        mock_func = Mock(return_value="sync_success")
        
        result = await retry_mechanism.execute_with_retry(mock_func, "arg1")
        
        assert result == "sync_success"
        mock_func.assert_called_once_with("arg1")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, retry_mechanism):
        """Test circuit breaker integration."""
        mock_func = AsyncMock(side_effect=ConnectionError("Connection failed"))
        circuit_breaker_config = CircuitBreakerConfig(failure_threshold=2)
        
        # First call should fail and record failure
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(
                mock_func,
                circuit_breaker_key="test_service",
                circuit_breaker_config=circuit_breaker_config
            )
        
        # Second call should also fail and open circuit breaker
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(
                mock_func,
                circuit_breaker_key="test_service",
                circuit_breaker_config=circuit_breaker_config
            )
        
        # Third call should fail immediately due to open circuit breaker
        with pytest.raises(Exception, match="Circuit breaker.*is OPEN"):
            await retry_mechanism.execute_with_retry(
                mock_func,
                circuit_breaker_key="test_service",
                circuit_breaker_config=circuit_breaker_config
            )
    
    def test_calculate_delay(self, retry_mechanism):
        """Test delay calculation with exponential backoff."""
        # Test without jitter (jitter is disabled in fixture)
        delay_0 = retry_mechanism._calculate_delay(0)
        delay_1 = retry_mechanism._calculate_delay(1)
        delay_2 = retry_mechanism._calculate_delay(2)
        
        assert delay_0 == 0.1  # base_delay
        assert delay_1 == 0.2  # base_delay * 2^1
        assert delay_2 == 0.4  # base_delay * 2^2
    
    def test_calculate_delay_with_max_limit(self):
        """Test delay calculation respects max_delay."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
        retry_mechanism = RetryMechanism(config)
        
        delay_5 = retry_mechanism._calculate_delay(5)  # Would be 10 * 2^5 = 320
        
        assert delay_5 == 15.0  # Capped at max_delay
    
    def test_is_retryable_exception(self, retry_mechanism):
        """Test retryable exception detection."""
        assert retry_mechanism._is_retryable_exception(ConnectionError()) is True
        assert retry_mechanism._is_retryable_exception(TimeoutError()) is True
        assert retry_mechanism._is_retryable_exception(ValueError()) is False
        assert retry_mechanism._is_retryable_exception(TypeError()) is False
    
    def test_get_circuit_breaker_status(self, retry_mechanism):
        """Test getting circuit breaker status."""
        # Non-existent circuit breaker
        status = retry_mechanism.get_circuit_breaker_status("nonexistent")
        assert status["status"] == "not_found"
        
        # Create a circuit breaker
        retry_mechanism._get_circuit_breaker("test_service")
        status = retry_mechanism.get_circuit_breaker_status("test_service")
        
        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 0
        assert status["last_failure_time"] is None
        assert status["can_attempt"] is True
    
    def test_reset_circuit_breaker(self, retry_mechanism):
        """Test resetting circuit breaker."""
        # Non-existent circuit breaker
        result = retry_mechanism.reset_circuit_breaker("nonexistent")
        assert result is False
        
        # Create and break a circuit breaker
        breaker = retry_mechanism._get_circuit_breaker("test_service")
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.failure_count == 2
        
        # Reset it
        result = retry_mechanism.reset_circuit_breaker("test_service")
        assert result is True
        assert breaker.failure_count == 0
        assert breaker.state == "CLOSED"


class TestWithRetryDecorator:
    """Test cases for the with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Test decorator on async functions."""
        call_count = 0
        
        @with_retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def test_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await test_async_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_sync_function_decorator(self):
        """Test decorator on synchronous functions."""
        call_count = 0
        
        @with_retry(max_attempts=3, base_delay=0.01, jitter=False)
        def test_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = test_sync_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_decorator_with_circuit_breaker(self):
        """Test decorator with circuit breaker functionality."""
        @with_retry(max_attempts=2, circuit_breaker_key="test_decorator")
        async def failing_func():
            raise ConnectionError("Always fails")
        
        # First call should fail after retries
        with pytest.raises(ConnectionError):
            await failing_func()
        
        # Second call should fail after retries and open circuit breaker
        with pytest.raises(ConnectionError):
            await failing_func()


class TestExecuteWithFallback:
    """Test cases for execute_with_fallback function."""
    
    @pytest.mark.asyncio
    async def test_primary_success(self):
        """Test successful primary function execution."""
        primary_func = AsyncMock(return_value="primary_result")
        fallback_func = AsyncMock(return_value="fallback_result")
        
        result = await execute_with_fallback(primary_func, fallback_func, "arg1")
        
        assert result == "primary_result"
        primary_func.assert_called_once_with("arg1")
        fallback_func.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_primary_failure_fallback_success(self):
        """Test fallback execution when primary fails."""
        primary_func = AsyncMock(side_effect=ConnectionError("Primary failed"))
        fallback_func = AsyncMock(return_value="fallback_result")
        
        result = await execute_with_fallback(primary_func, fallback_func, "arg1")
        
        assert result == "fallback_result"
        fallback_func.assert_called_once_with("arg1")
    
    @pytest.mark.asyncio
    async def test_both_functions_fail(self):
        """Test behavior when both primary and fallback fail."""
        primary_func = AsyncMock(side_effect=ConnectionError("Primary failed"))
        fallback_func = AsyncMock(side_effect=ValueError("Fallback failed"))
        
        with pytest.raises(ValueError, match="Fallback failed"):
            await execute_with_fallback(primary_func, fallback_func, "arg1")
    
    @pytest.mark.asyncio
    async def test_sync_functions(self):
        """Test with synchronous functions."""
        primary_func = Mock(side_effect=ConnectionError("Primary failed"))
        fallback_func = Mock(return_value="fallback_result")
        
        result = await execute_with_fallback(primary_func, fallback_func, "arg1")
        
        assert result == "fallback_result"
        fallback_func.assert_called_once_with("arg1")
    
    @pytest.mark.asyncio
    async def test_no_retry_primary(self):
        """Test with retry_primary=False."""
        call_count = 0
        
        def primary_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")
        
        fallback_func = Mock(return_value="fallback_result")
        
        result = await execute_with_fallback(
            primary_func, fallback_func, retry_primary=False
        )
        
        assert result == "fallback_result"
        assert call_count == 1  # No retries


class TestDefaultRetryMechanism:
    """Test cases for the default retry mechanism instance."""
    
    def test_default_instance_exists(self):
        """Test that default retry mechanism instance exists."""
        assert default_retry_mechanism is not None
        assert isinstance(default_retry_mechanism, RetryMechanism)
    
    @pytest.mark.asyncio
    async def test_default_instance_functionality(self):
        """Test that default instance works correctly."""
        mock_func = AsyncMock(return_value="success")
        
        result = await default_retry_mechanism.execute_with_retry(mock_func, "test_arg")
        
        assert result == "success"
        mock_func.assert_called_once_with("test_arg")


class TestRetryMechanismEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_zero_max_attempts(self):
        """Test behavior with zero max attempts."""
        config = RetryConfig(max_attempts=0)
        retry_mechanism = RetryMechanism(config)
        
        mock_func = AsyncMock(side_effect=ConnectionError("Should not retry"))
        
        with pytest.raises(ConnectionError):
            await retry_mechanism.execute_with_retry(mock_func)
        
        # Should not call the function at all
        mock_func.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_negative_delays(self):
        """Test behavior with negative delay values."""
        config = RetryConfig(base_delay=-1.0, max_delay=-5.0)
        retry_mechanism = RetryMechanism(config)
        
        # Should not cause issues, delays should be clamped to 0
        delay = retry_mechanism._calculate_delay(1)
        assert delay >= 0
    
    def test_empty_retryable_exceptions(self):
        """Test behavior with empty retryable exceptions list."""
        config = RetryConfig(retryable_exceptions=[])
        retry_mechanism = RetryMechanism(config)
        
        # No exceptions should be retryable
        assert retry_mechanism._is_retryable_exception(ConnectionError()) is False
        assert retry_mechanism._is_retryable_exception(TimeoutError()) is False
    
    @pytest.mark.asyncio
    async def test_function_with_no_args(self, retry_mechanism):
        """Test function execution with no arguments."""
        mock_func = AsyncMock(return_value="no_args_result")
        
        result = await retry_mechanism.execute_with_retry(mock_func)
        
        assert result == "no_args_result"
        mock_func.assert_called_once_with()
    
    @pytest.mark.asyncio
    async def test_function_with_complex_args(self, retry_mechanism):
        """Test function execution with complex arguments."""
        mock_func = AsyncMock(return_value="complex_result")
        
        complex_arg = {"nested": {"data": [1, 2, 3]}}
        result = await retry_mechanism.execute_with_retry(
            mock_func, 
            "string_arg", 
            42, 
            complex_arg,
            keyword_arg="value",
            another_kwarg=True
        )
        
        assert result == "complex_result"
        mock_func.assert_called_once_with(
            "string_arg", 
            42, 
            complex_arg,
            keyword_arg="value",
            another_kwarg=True
        )