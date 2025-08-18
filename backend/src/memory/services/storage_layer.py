"""
Storage layer service implementation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from ..interfaces.storage_layer import StorageLayerInterface
from ..models import (
    Conversation, ConversationSummary, UserPreferences, 
    PrivacySettings, SearchResult
)
from ..utils.storage_backends import HybridStorageBackend


class StorageLayer(StorageLayerInterface):
    """Storage layer service implementation using hybrid storage backend."""
    
    def __init__(self):
        """Initialize the storage layer."""
        self._backend = HybridStorageBackend()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the storage layer."""
        if not self._initialized:
            await self._backend.initialize()
            self._initialized = True
    
    async def close(self) -> None:
        """Close the storage layer."""
        if self._initialized:
            await self._backend.close()
            self._initialized = False
    
    # Conversation storage
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store a conversation."""
        await self._ensure_initialized()
        return await self._backend.store_conversation(conversation)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a specific conversation."""
        await self._ensure_initialized()
        return await self._backend.get_conversation(conversation_id)
    
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get conversations for a user."""
        await self._ensure_initialized()
        return await self._backend.get_user_conversations(user_id, limit, start_date, end_date)
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a specific conversation."""
        await self._ensure_initialized()
        return await self._backend.delete_conversation(conversation_id)
    
    # Conversation summaries
    async def store_conversation_summary(self, summary: ConversationSummary) -> None:
        """Store a conversation summary."""
        await self._ensure_initialized()
        return await self._backend.store_conversation_summary(summary)
    
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries for a user."""
        await self._ensure_initialized()
        return await self._backend.get_conversation_summaries(user_id, limit)
    
    # User preferences
    async def store_user_preferences(self, preferences: UserPreferences) -> None:
        """Store user preferences."""
        await self._ensure_initialized()
        return await self._backend.store_user_preferences(preferences)
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences."""
        await self._ensure_initialized()
        return await self._backend.get_user_preferences(user_id)
    
    # Privacy settings
    async def store_privacy_settings(self, settings: PrivacySettings) -> None:
        """Store privacy settings."""
        await self._ensure_initialized()
        return await self._backend.store_privacy_settings(settings)
    
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings."""
        await self._ensure_initialized()
        return await self._backend.get_privacy_settings(user_id)
    
    # Data management
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all data for a user."""
        await self._ensure_initialized()
        return await self._backend.delete_all_user_data(user_id)
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of all user data."""
        await self._ensure_initialized()
        return await self._backend.get_user_data_summary(user_id)
    
    # Health and maintenance
    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        await self._ensure_initialized()
        return await self._backend.health_check()
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data according to retention policies."""
        await self._ensure_initialized()
        return await self._backend.cleanup_expired_data()
    
    async def _ensure_initialized(self) -> None:
        """Ensure the storage layer is initialized."""
        if not self._initialized:
            await self.initialize()