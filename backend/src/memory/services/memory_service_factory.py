"""
Memory service factory for creating and configuring the complete memory service.
"""

import logging
from typing import Optional
from ..config import get_memory_config
from ..interfaces import MemoryServiceInterface
from .memory_service import MemoryService
from .context_manager import ContextManager
from .preference_engine import PreferenceEngine
from .search_service import SearchService
from .privacy_controller import PrivacyController
from .storage_layer import StorageLayer

logger = logging.getLogger(__name__)


class MemoryServiceFactory:
    """Factory for creating and configuring memory service instances."""
    
    @staticmethod
    async def create_memory_service(
        storage_layer: Optional[StorageLayer] = None,
        auto_initialize: bool = True
    ) -> MemoryServiceInterface:
        """
        Create a fully configured memory service instance.
        
        Args:
            storage_layer: Optional storage layer instance. If None, creates a new one.
            auto_initialize: Whether to automatically initialize the service.
            
        Returns:
            Configured MemoryService instance.
        """
        config = get_memory_config()
        
        try:
            # Create storage layer if not provided
            if storage_layer is None:
                storage_layer = StorageLayer()
            
            # Create service components
            context_manager = ContextManager(storage_layer)
            preference_engine = PreferenceEngine()
            search_service = SearchService()
            privacy_controller = PrivacyController(storage_layer)
            
            # Create the main memory service
            memory_service = MemoryService(
                context_manager=context_manager,
                preference_engine=preference_engine,
                search_service=search_service,
                privacy_controller=privacy_controller,
                storage_layer=storage_layer
            )
            
            # Initialize if requested
            if auto_initialize:
                await memory_service.initialize()
                logger.info("Memory service created and initialized successfully")
            else:
                logger.info("Memory service created (not initialized)")
            
            return memory_service
            
        except Exception as e:
            logger.error(f"Failed to create memory service: {e}")
            raise


class MemoryServiceCoordinator:
    """Coordinates multiple memory service instances and manages service lifecycle."""
    
    def __init__(self):
        """Initialize the service coordinator."""
        self._services = {}
        self._config = get_memory_config()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the service coordinator."""
        if self._initialized:
            return
        
        try:
            # Perform any global initialization tasks
            logger.info("Memory service coordinator initialized")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize service coordinator: {e}")
            raise
    
    async def get_service(self, service_id: str = "default") -> MemoryServiceInterface:
        """
        Get or create a memory service instance.
        
        Args:
            service_id: Identifier for the service instance.
            
        Returns:
            MemoryService instance.
        """
        await self._ensure_initialized()
        
        if service_id not in self._services:
            self._services[service_id] = await MemoryServiceFactory.create_memory_service()
            logger.info(f"Created new memory service instance: {service_id}")
        
        return self._services[service_id]
    
    async def remove_service(self, service_id: str) -> None:
        """
        Remove a memory service instance.
        
        Args:
            service_id: Identifier for the service instance to remove.
        """
        if service_id in self._services:
            # Perform any cleanup if needed
            del self._services[service_id]
            logger.info(f"Removed memory service instance: {service_id}")
    
    async def health_check_all(self) -> dict:
        """
        Perform health check on all managed services.
        
        Returns:
            Dictionary with health status of all services.
        """
        await self._ensure_initialized()
        
        health_status = {
            "coordinator": "healthy",
            "services": {}
        }
        
        for service_id, service in self._services.items():
            try:
                service_health = await service.health_check()
                health_status["services"][service_id] = service_health
            except Exception as e:
                health_status["services"][service_id] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_status
    
    async def shutdown(self) -> None:
        """Shutdown all services and cleanup resources."""
        logger.info("Shutting down memory service coordinator")
        
        for service_id in list(self._services.keys()):
            await self.remove_service(service_id)
        
        self._initialized = False
        logger.info("Memory service coordinator shutdown complete")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the coordinator is initialized."""
        if not self._initialized:
            await self.initialize()


# Global coordinator instance
_coordinator = None


async def get_memory_service_coordinator() -> MemoryServiceCoordinator:
    """Get the global memory service coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = MemoryServiceCoordinator()
        await _coordinator.initialize()
    return _coordinator


async def get_default_memory_service() -> MemoryServiceInterface:
    """Get the default memory service instance."""
    coordinator = await get_memory_service_coordinator()
    return await coordinator.get_service("default")


def get_memory_service() -> MemoryServiceInterface:
    """
    Synchronous function to get memory service instance.
    
    This is a convenience function for use in FastAPI dependencies and other
    synchronous contexts. It returns a service that can be initialized later.
    
    Returns:
        MemoryService instance (not yet initialized).
    """
    try:
        # Create a basic memory service without initialization
        storage_layer = StorageLayer()
        context_manager = ContextManager(storage_layer)
        preference_engine = PreferenceEngine()
        search_service = SearchService()
        privacy_controller = PrivacyController(storage_layer)
        
        memory_service = MemoryService(
            context_manager=context_manager,
            preference_engine=preference_engine,
            search_service=search_service,
            privacy_controller=privacy_controller,
            storage_layer=storage_layer
        )
        
        logger.debug("Created memory service instance (not initialized)")
        return memory_service
        
    except Exception as e:
        logger.error(f"Failed to create memory service: {e}")
        raise