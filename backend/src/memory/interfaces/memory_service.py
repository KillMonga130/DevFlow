"""
Main memory service interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..models import (
    Conversation, ConversationContext, SearchQuery, SearchResult,
    DeleteOptions, UserDataExport, PrivacySettings
)


class MemoryServiceInterface(ABC):
    """Interface for the main memory service."""
    
    @abstractmethod
    async def store_conversation(self, user_id: str, conversation: Conversation) -> None:
        """Store a conversation in memory."""
        pass
    
    @abstractmethod
    async def retrieve_context(self, user_id: str, limit: Optional[int] = None) -> ConversationContext:
        """Retrieve conversation context for a user."""
        pass
    
    @abstractmethod
    async def search_history(self, user_id: str, query: SearchQuery) -> List[SearchResult]:
        """Search through conversation history."""
        pass
    
    @abstractmethod
    async def delete_user_data(self, user_id: str, options: Optional[DeleteOptions] = None) -> None:
        """Delete user data according to specified options."""
        pass
    
    @abstractmethod
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data."""
        pass
    
    @abstractmethod
    async def update_privacy_settings(self, user_id: str, settings: PrivacySettings) -> None:
        """Update user privacy settings."""
        pass
    
    @abstractmethod
    async def get_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get user privacy settings."""
        pass