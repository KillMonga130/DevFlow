"""
Main memory service implementation.
"""

import logging
from typing import Optional, List
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
from .context_manager import ContextManager
from .preference_engine import PreferenceEngine
from .search_service import SearchService
from .privacy_controller import PrivacyController
from .storage_layer import StorageLayer

logger = logging.getLogger(__name__)


class MemoryService(MemoryServiceInterface):
    """Main memory service implementation that orchestrates all memory components."""
    
    def __init__(
        self,
        context_manager: Optional[ContextManagerInterface] = None,
        preference_engine: Optional[PreferenceEngineInterface] = None,
        search_service: Optional[SearchServiceInterface] = None,
        privacy_controller: Optional[PrivacyControllerInterface] = None,
        storage_layer: Optional[StorageLayer] = None
    ):
        """Initialize the memory service with all component dependencies."""
        self._config = get_memory_config()
        self._storage = storage_layer or StorageLayer()
        
        # Initialize service components
        self._context_manager = context_manager or ContextManager(self._storage)
        self._preference_engine = preference_engine or PreferenceEngine()
        self._search_service = search_service or SearchService()
        self._privacy_controller = privacy_controller or PrivacyController(self._storage)
        
        self._initialized = False
        logger.info("MemoryService initialized with all components")
    
    async def initialize(self) -> None:
        """Initialize all service components."""
        if self._initialized:
            return
            
        try:
            # Initialize storage layer first
            await self._storage.initialize()
            
            # Initialize privacy controller
            if hasattr(self._privacy_controller, 'initialize'):
                await self._privacy_controller.initialize()
            
            # Initialize preference engine if it has initialization
            if hasattr(self._preference_engine, 'initialize'):
                await self._preference_engine.initialize()
            
            self._initialized = True
            logger.info("MemoryService fully initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MemoryService: {e}")
            raise
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized before operations."""
        if not self._initialized:
            await self.initialize()
    
    async def store_conversation(self, user_id: str, conversation: Conversation) -> None:
        """Store a conversation in memory with full processing."""
        await self._ensure_initialized()
        
        try:
            # Store the conversation in the storage layer
            await self._storage.store_conversation(conversation)
            
            # Index the conversation for search
            conversation_content = " ".join([msg.content for msg in conversation.messages])
            await self._search_service.index_conversation(
                user_id, conversation.id, conversation_content
            )
            
            # Update context with the new conversation
            if conversation.messages:
                last_exchange = MessageExchange(
                    user_message=conversation.messages[-2] if len(conversation.messages) >= 2 else None,
                    assistant_message=conversation.messages[-1] if conversation.messages else None
                )
                await self._context_manager.update_context(user_id, last_exchange)
            
            # Learn preferences from the conversation if enabled
            if self._config.preference_learning_enabled:
                await self._preference_engine.analyze_user_preferences(user_id, [conversation])
            
            # Log the operation for audit
            await self._privacy_controller.audit_data_access(
                user_id, "STORE_CONVERSATION", f"Stored conversation {conversation.id}"
            )
            
            logger.info(f"Successfully stored conversation {conversation.id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store conversation for user {user_id}: {e}")
            # Implement fallback mechanism - at minimum try to store in basic storage
            try:
                await self._storage.store_conversation(conversation)
                logger.warning(f"Stored conversation with limited functionality due to error: {e}")
            except Exception as fallback_error:
                logger.error(f"Complete failure to store conversation: {fallback_error}")
                raise
    
    async def retrieve_context(self, user_id: str, limit: Optional[int] = None) -> ConversationContext:
        """Retrieve conversation context for a user with fallback mechanisms."""
        await self._ensure_initialized()
        
        try:
            # Build context using the context manager
            context = await self._context_manager.build_context(user_id, "")
            
            # Apply user preferences to the context if available
            try:
                user_preferences = await self._preference_engine.get_preferences(user_id)
                context.user_preferences = user_preferences
            except Exception as pref_error:
                logger.warning(f"Failed to load preferences for user {user_id}: {pref_error}")
                # Continue without preferences
            
            # Log the operation for audit
            await self._privacy_controller.audit_data_access(
                user_id, "RETRIEVE_CONTEXT", "Retrieved conversation context"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to retrieve context for user {user_id}: {e}")
            # Fallback to basic context
            try:
                return ConversationContext(user_id=user_id)
            except Exception as fallback_error:
                logger.error(f"Complete failure to retrieve context: {fallback_error}")
                raise
    
    async def search_history(self, user_id: str, query: SearchQuery) -> List[SearchResult]:
        """Search through conversation history with privacy controls."""
        await self._ensure_initialized()
        
        try:
            # Check privacy settings first
            privacy_settings = await self.get_privacy_settings(user_id)
            if not privacy_settings.allow_search_indexing:
                logger.info(f"Search disabled for user {user_id} due to privacy settings")
                return []
            
            # Perform the search
            results = await self._search_service.search_conversations(query)
            
            # Log the operation for audit
            await self._privacy_controller.audit_data_access(
                user_id, "SEARCH_HISTORY", f"Searched with query: {query.keywords}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search history for user {user_id}: {e}")
            # Return empty results on failure
            return []
    
    async def delete_user_data(self, user_id: str, options: Optional[DeleteOptions] = None) -> None:
        """Delete user data according to specified options."""
        await self._ensure_initialized()
        
        if options is None:
            # Create default delete options for complete data removal
            from ..models.privacy import DeleteScope
            options = DeleteOptions(
                scope=DeleteScope.ALL_DATA,
                confirm_deletion=True,
                reason="User requested data deletion"
            )
        
        try:
            # Use privacy controller to handle the deletion
            await self._privacy_controller.delete_user_data(user_id, options)
            
            # Remove from search index
            # Note: This would need to be implemented in search service
            # await self._search_service.remove_user_from_index(user_id)
            
            logger.info(f"Successfully deleted data for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            raise
    
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data."""
        await self._ensure_initialized()
        
        try:
            # Use privacy controller to handle the export
            export_data = await self._privacy_controller.export_user_data(user_id)
            
            logger.info(f"Successfully exported data for user {user_id}")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export user data for {user_id}: {e}")
            raise
    
    async def update_privacy_settings(self, user_id: str, settings: PrivacySettings) -> None:
        """Update user privacy settings."""
        await self._ensure_initialized()
        
        try:
            # Store privacy settings through storage layer
            await self._storage.store_privacy_settings(settings)
            
            # Apply retention policy if specified
            if hasattr(settings, 'retention_policy') and settings.retention_policy:
                await self._privacy_controller.apply_retention_policy(user_id, settings)
            
            # Log the operation for audit
            await self._privacy_controller.audit_data_access(
                user_id, "UPDATE_PRIVACY_SETTINGS", "Updated privacy settings"
            )
            
            logger.info(f"Updated privacy settings for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update privacy settings for user {user_id}: {e}")
            raise
    
    async def get_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get user privacy settings."""
        await self._ensure_initialized()
        
        try:
            # Retrieve privacy settings from storage
            settings = await self._storage.get_privacy_settings(user_id)
            
            # Log the operation for audit
            await self._privacy_controller.audit_data_access(
                user_id, "GET_PRIVACY_SETTINGS", "Retrieved privacy settings"
            )
            
            return settings
            
        except Exception as e:
            logger.error(f"Failed to get privacy settings for user {user_id}: {e}")
            # Return default privacy settings
            return PrivacySettings(user_id=user_id)
    
    async def health_check(self) -> dict:
        """Perform a health check on all service components."""
        health_status = {
            "memory_service": "healthy",
            "components": {},
            "initialized": self._initialized
        }
        
        try:
            await self._ensure_initialized()
            
            # Check storage layer
            try:
                await self._storage.health_check()
                health_status["components"]["storage"] = "healthy"
            except Exception as e:
                health_status["components"]["storage"] = f"unhealthy: {e}"
            
            # Check other components if they have health check methods
            for component_name, component in [
                ("context_manager", self._context_manager),
                ("preference_engine", self._preference_engine),
                ("search_service", self._search_service),
                ("privacy_controller", self._privacy_controller)
            ]:
                if hasattr(component, 'health_check'):
                    try:
                        await component.health_check()
                        health_status["components"][component_name] = "healthy"
                    except Exception as e:
                        health_status["components"][component_name] = f"unhealthy: {e}"
                else:
                    health_status["components"][component_name] = "no health check available"
            
        except Exception as e:
            health_status["memory_service"] = f"unhealthy: {e}"
        
        return health_status