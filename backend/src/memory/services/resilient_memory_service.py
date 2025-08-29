"""
Resilient memory service with fallback mechanisms and error recovery.
"""

import logging
from typing import Optional, List, Dict, Any
from ..interfaces import MemoryServiceInterface
from ..interfaces import (
    ContextManagerInterface, PreferenceEngineInterface,
    SearchServiceInterface, PrivacyControllerInterface
)
from ..models import (
    Conversation, ConversationContext, SearchQuery, SearchResult,
    DeleteOptions, UserDataExport, PrivacySettings, MessageExchange
)
from ..config import get_memory_config
from .memory_service import MemoryService
from .fallback_context_service import FallbackContextService
from .storage_layer import StorageLayer
from ..utils.retry_mechanism import (
    RetryMechanism, RetryConfig, CircuitBreakerConfig, execute_with_fallback
)

logger = logging.getLogger(__name__)


class ResilientMemoryService(MemoryServiceInterface):
    """
    Memory service with enhanced error handling, fallback mechanisms, and resilience patterns.
    """
    
    def __init__(
        self,
        primary_service: Optional[MemoryService] = None,
        fallback_context_service: Optional[FallbackContextService] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """Initialize the resilient memory service."""
        self._config = get_memory_config()
        
        # Primary service (full functionality)
        self._primary_service = primary_service or MemoryService()
        
        # Fallback services
        self._fallback_context_service = fallback_context_service or FallbackContextService()
        
        # Retry mechanism
        retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=[
                ConnectionError,
                TimeoutError,
                OSError,
                Exception  # Catch-all for now, can be refined
            ]
        )
        self._retry_mechanism = RetryMechanism(retry_config)
        
        # Circuit breaker configurations
        self._circuit_breaker_configs = {
            'storage': CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
            'context': CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0),
            'search': CircuitBreakerConfig(failure_threshold=5, recovery_timeout=45.0),
            'preferences': CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
        }
        
        # Service state tracking
        self._service_health = {
            'primary_service': True,
            'storage': True,
            'context': True,
            'search': True,
            'preferences': True
        }
        
        self._degraded_mode = False
        self._initialized = False
        
        logger.info("ResilientMemoryService initialized with fallback mechanisms")
    
    async def initialize(self) -> None:
        """Initialize the resilient memory service with fallback handling."""
        if self._initialized:
            return
        
        try:
            # Try to initialize primary service
            await self._retry_mechanism.execute_with_retry(
                self._primary_service.initialize,
                circuit_breaker_key='primary_service',
                circuit_breaker_config=CircuitBreakerConfig(failure_threshold=2, recovery_timeout=120.0)
            )
            
            self._service_health['primary_service'] = True
            logger.info("Primary memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize primary memory service: {e}")
            self._service_health['primary_service'] = False
            self._degraded_mode = True
            logger.warning("Operating in degraded mode with fallback services only")
        
        # Initialize fallback service (should always succeed)
        try:
            if hasattr(self._fallback_context_service, 'initialize'):
                await self._fallback_context_service.initialize()
            logger.info("Fallback context service ready")
        except Exception as e:
            logger.error(f"Failed to initialize fallback service: {e}")
        
        self._initialized = True
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def store_conversation(self, user_id: str, conversation: Conversation) -> None:
        """Store conversation with fallback mechanisms."""
        await self._ensure_initialized()
        
        async def primary_store():
            return await self._primary_service.store_conversation(user_id, conversation)
        
        async def fallback_store():
            # In fallback mode, we can only update the context service
            if conversation.messages:
                last_exchange = MessageExchange(
                    user_message=conversation.messages[-2] if len(conversation.messages) >= 2 else None,
                    assistant_message=conversation.messages[-1] if conversation.messages else None
                )
                await self._fallback_context_service.update_context(user_id, last_exchange)
            
            logger.warning(f"Stored conversation {conversation.id} in fallback mode only")
        
        try:
            if self._service_health['primary_service'] and not self._degraded_mode:
                await self._retry_mechanism.execute_with_retry(
                    primary_store,
                    circuit_breaker_key='storage',
                    circuit_breaker_config=self._circuit_breaker_configs['storage']
                )
            else:
                await fallback_store()
                
        except Exception as e:
            logger.error(f"Primary storage failed for conversation {conversation.id}: {e}")
            self._service_health['storage'] = False
            
            try:
                await fallback_store()
            except Exception as fallback_error:
                logger.error(f"Fallback storage also failed: {fallback_error}")
                raise fallback_error
    
    async def retrieve_context(self, user_id: str, limit: Optional[int] = None) -> ConversationContext:
        """Retrieve context with intelligent fallback."""
        await self._ensure_initialized()
        
        async def primary_retrieve():
            return await self._primary_service.retrieve_context(user_id, limit)
        
        async def fallback_retrieve():
            return await self._fallback_context_service.build_context(user_id, "")
        
        try:
            if self._service_health['primary_service'] and self._service_health['context']:
                return await self._retry_mechanism.execute_with_retry(
                    primary_retrieve,
                    circuit_breaker_key='context',
                    circuit_breaker_config=self._circuit_breaker_configs['context']
                )
            else:
                logger.info(f"Using fallback context retrieval for user {user_id}")
                return await fallback_retrieve()
                
        except Exception as e:
            logger.error(f"Primary context retrieval failed for user {user_id}: {e}")
            self._service_health['context'] = False
            
            try:
                return await fallback_retrieve()
            except Exception as fallback_error:
                logger.error(f"Fallback context retrieval also failed: {fallback_error}")
                # Return absolute minimal context
                return ConversationContext(
                    user_id=user_id,
                    context_summary="Error retrieving context - minimal mode",
                    context_timestamp=conversation.timestamp if 'conversation' in locals() else None
                )
    
    async def search_history(self, user_id: str, query: SearchQuery) -> List[SearchResult]:
        """Search history with graceful degradation."""
        await self._ensure_initialized()
        
        async def primary_search():
            return await self._primary_service.search_history(user_id, query)
        
        async def fallback_search():
            logger.warning(f"Search functionality unavailable in fallback mode for user {user_id}")
            return []
        
        try:
            if self._service_health['primary_service'] and self._service_health['search']:
                return await self._retry_mechanism.execute_with_retry(
                    primary_search,
                    circuit_breaker_key='search',
                    circuit_breaker_config=self._circuit_breaker_configs['search']
                )
            else:
                return await fallback_search()
                
        except Exception as e:
            logger.error(f"Search failed for user {user_id}: {e}")
            self._service_health['search'] = False
            return await fallback_search()
    
    async def delete_user_data(self, user_id: str, options: Optional[DeleteOptions] = None) -> None:
        """Delete user data with error handling."""
        await self._ensure_initialized()
        
        if not self._service_health['primary_service']:
            raise Exception("Data deletion requires primary service - not available in fallback mode")
        
        try:
            await self._retry_mechanism.execute_with_retry(
                self._primary_service.delete_user_data,
                user_id,
                options,
                circuit_breaker_key='storage',
                circuit_breaker_config=self._circuit_breaker_configs['storage']
            )
            
            # Also clear fallback cache
            await self._fallback_context_service.prune_old_context(user_id)
            
        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            raise
    
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export user data with error handling."""
        await self._ensure_initialized()
        
        if not self._service_health['primary_service']:
            raise Exception("Data export requires primary service - not available in fallback mode")
        
        try:
            return await self._retry_mechanism.execute_with_retry(
                self._primary_service.export_user_data,
                user_id,
                circuit_breaker_key='storage',
                circuit_breaker_config=self._circuit_breaker_configs['storage']
            )
            
        except Exception as e:
            logger.error(f"Failed to export user data for {user_id}: {e}")
            raise
    
    async def update_privacy_settings(self, user_id: str, settings: PrivacySettings) -> None:
        """Update privacy settings with error handling."""
        await self._ensure_initialized()
        
        if not self._service_health['primary_service']:
            logger.warning(f"Privacy settings update limited in fallback mode for user {user_id}")
            return
        
        try:
            await self._retry_mechanism.execute_with_retry(
                self._primary_service.update_privacy_settings,
                user_id,
                settings,
                circuit_breaker_key='storage',
                circuit_breaker_config=self._circuit_breaker_configs['storage']
            )
            
        except Exception as e:
            logger.error(f"Failed to update privacy settings for {user_id}: {e}")
            raise
    
    async def get_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get privacy settings with fallback to defaults."""
        await self._ensure_initialized()
        
        async def primary_get():
            return await self._primary_service.get_privacy_settings(user_id)
        
        async def fallback_get():
            logger.info(f"Returning default privacy settings for user {user_id}")
            return PrivacySettings(user_id=user_id)
        
        try:
            if self._service_health['primary_service']:
                return await self._retry_mechanism.execute_with_retry(
                    primary_get,
                    circuit_breaker_key='storage',
                    circuit_breaker_config=self._circuit_breaker_configs['storage']
                )
            else:
                return await fallback_get()
                
        except Exception as e:
            logger.error(f"Failed to get privacy settings for {user_id}: {e}")
            return await fallback_get()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with service status."""
        health_status = {
            "service": "resilient_memory_service",
            "status": "healthy" if not self._degraded_mode else "degraded",
            "initialized": self._initialized,
            "degraded_mode": self._degraded_mode,
            "service_health": self._service_health.copy(),
            "circuit_breakers": {},
            "fallback_services": {}
        }
        
        # Check circuit breaker status
        for key in self._circuit_breaker_configs.keys():
            health_status["circuit_breakers"][key] = self._retry_mechanism.get_circuit_breaker_status(key)
        
        # Check primary service if available
        if self._service_health['primary_service']:
            try:
                primary_health = await self._primary_service.health_check()
                health_status["primary_service"] = primary_health
            except Exception as e:
                health_status["primary_service"] = {"status": "unhealthy", "error": str(e)}
                self._service_health['primary_service'] = False
        
        # Check fallback services
        try:
            fallback_health = await self._fallback_context_service.health_check()
            health_status["fallback_services"]["context"] = fallback_health
        except Exception as e:
            health_status["fallback_services"]["context"] = {"status": "unhealthy", "error": str(e)}
        
        return health_status
    
    async def recover_service(self, service_name: str) -> bool:
        """Attempt to recover a failed service."""
        try:
            if service_name == 'primary_service':
                await self._primary_service.initialize()
                self._service_health['primary_service'] = True
                self._degraded_mode = False
                logger.info("Primary service recovered successfully")
                return True
            
            elif service_name in self._circuit_breaker_configs:
                # Reset circuit breaker
                self._retry_mechanism.reset_circuit_breaker(service_name)
                self._service_health[service_name] = True
                logger.info(f"Service {service_name} circuit breaker reset")
                return True
            
            else:
                logger.warning(f"Unknown service name for recovery: {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to recover service {service_name}: {e}")
            return False
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get metrics about service performance and health."""
        metrics = {
            "service_health": self._service_health.copy(),
            "degraded_mode": self._degraded_mode,
            "circuit_breaker_status": {},
            "fallback_cache_stats": {}
        }
        
        # Circuit breaker metrics
        for key in self._circuit_breaker_configs.keys():
            metrics["circuit_breaker_status"][key] = self._retry_mechanism.get_circuit_breaker_status(key)
        
        # Fallback service metrics
        try:
            metrics["fallback_cache_stats"] = self._fallback_context_service.get_cache_stats()
        except Exception as e:
            metrics["fallback_cache_stats"] = {"error": str(e)}
        
        return metrics
    
    async def force_degraded_mode(self, enable: bool = True) -> None:
        """Force the service into or out of degraded mode for testing."""
        self._degraded_mode = enable
        if enable:
            logger.warning("Forced into degraded mode")
        else:
            logger.info("Forced out of degraded mode")
    
    async def cleanup_fallback_cache(self) -> None:
        """Clean up fallback cache data."""
        try:
            # This would need to be implemented in the fallback service
            if hasattr(self._fallback_context_service, '_basic_cache'):
                cache_size_before = len(self._fallback_context_service._basic_cache)
                self._fallback_context_service._basic_cache.clear()
                logger.info(f"Cleared {cache_size_before} entries from fallback cache")
        except Exception as e:
            logger.error(f"Error cleaning up fallback cache: {e}")