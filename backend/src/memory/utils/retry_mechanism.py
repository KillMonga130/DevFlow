"""
Retry mechanism utilities for handling transient failures.
"""

import asyncio
import logging
import random
from typing import Callable, Any, Optional, Type, Union, List
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
            # Add database-specific exceptions as needed
        ]


class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception


class CircuitBreakerState:
    """State management for circuit breaker."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
    
    def can_attempt(self) -> bool:
        """Check if an attempt can be made."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)):
                self.state = "HALF_OPEN"
                return True
            return False
        
        # HALF_OPEN state
        return True


class RetryMechanism:
    """Advanced retry mechanism with circuit breaker pattern."""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self._circuit_breakers = {}
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        circuit_breaker_key: Optional[str] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and optional circuit breaker.
        
        Args:
            func: The function to execute
            *args: Arguments for the function
            circuit_breaker_key: Key for circuit breaker (if None, no circuit breaker)
            circuit_breaker_config: Configuration for circuit breaker
            **kwargs: Keyword arguments for the function
        
        Returns:
            The result of the function execution
        
        Raises:
            The last exception if all retries fail
        """
        # Check circuit breaker if enabled
        if circuit_breaker_key:
            circuit_breaker = self._get_circuit_breaker(circuit_breaker_key, circuit_breaker_config)
            if not circuit_breaker.can_attempt():
                raise Exception(f"Circuit breaker {circuit_breaker_key} is OPEN")
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # Record success in circuit breaker
                if circuit_breaker_key:
                    circuit_breaker.record_success()
                
                if attempt > 0:
                    logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    if circuit_breaker_key:
                        circuit_breaker.record_failure()
                    raise e
                
                # Record failure in circuit breaker
                if circuit_breaker_key:
                    circuit_breaker.record_failure()
                
                # Don't wait after the last attempt
                if attempt == self.retry_config.max_attempts - 1:
                    break
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
        
        logger.error(f"All {self.retry_config.max_attempts} attempts failed for {func.__name__}")
        raise last_exception
    
    def _get_circuit_breaker(
        self, 
        key: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreakerState:
        """Get or create a circuit breaker for the given key."""
        if key not in self._circuit_breakers:
            breaker_config = config or CircuitBreakerConfig()
            self._circuit_breakers[key] = CircuitBreakerState(breaker_config)
        
        return self._circuit_breakers[key]
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        return any(
            isinstance(exception, exc_type) 
            for exc_type in self.retry_config.retryable_exceptions
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt using exponential backoff."""
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)
        
        if self.retry_config.jitter:
            # Add jitter to prevent thundering herd
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def get_circuit_breaker_status(self, key: str) -> dict:
        """Get the status of a circuit breaker."""
        if key not in self._circuit_breakers:
            return {"status": "not_found"}
        
        breaker = self._circuit_breakers[key]
        return {
            "state": breaker.state,
            "failure_count": breaker.failure_count,
            "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
            "can_attempt": breaker.can_attempt()
        }
    
    def reset_circuit_breaker(self, key: str) -> bool:
        """Reset a circuit breaker to closed state."""
        if key in self._circuit_breakers:
            self._circuit_breakers[key].record_success()
            logger.info(f"Reset circuit breaker {key}")
            return True
        return False


# Decorator for easy retry functionality
def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    circuit_breaker_key: Optional[str] = None
):
    """
    Decorator to add retry functionality to a function.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to delays
        retryable_exceptions: List of exceptions that should trigger retries
        circuit_breaker_key: Key for circuit breaker (optional)
    """
    def decorator(func):
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions
        )
        retry_mechanism = RetryMechanism(retry_config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_mechanism.execute_with_retry(
                func, *args, circuit_breaker_key=circuit_breaker_key, **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(retry_mechanism.execute_with_retry(
                func, *args, circuit_breaker_key=circuit_breaker_key, **kwargs
            ))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Global retry mechanism instance
default_retry_mechanism = RetryMechanism()


async def execute_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args,
    retry_primary: bool = True,
    **kwargs
) -> Any:
    """
    Execute a primary function with a fallback function if it fails.
    
    Args:
        primary_func: The primary function to try first
        fallback_func: The fallback function to use if primary fails
        *args: Arguments for both functions
        retry_primary: Whether to retry the primary function
        **kwargs: Keyword arguments for both functions
    
    Returns:
        Result from primary function if successful, otherwise from fallback
    """
    try:
        if retry_primary:
            return await default_retry_mechanism.execute_with_retry(primary_func, *args, **kwargs)
        else:
            return await primary_func(*args, **kwargs) if asyncio.iscoroutinefunction(primary_func) else primary_func(*args, **kwargs)
    
    except Exception as e:
        logger.warning(f"Primary function {primary_func.__name__} failed: {e}. Using fallback.")
        
        try:
            return await fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_func) else fallback_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.error(f"Fallback function {fallback_func.__name__} also failed: {fallback_error}")
            raise fallback_error