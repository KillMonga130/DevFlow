"""
Storage layer interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models import (
    Conversation, ConversationSummary, UserPreferences, 
    PrivacySettings, SearchResult
)


class StorageLayerInterface(ABC):
    """Interface for the storage abstraction layer."""
    
    # Conversation storage
    @abstractmethod
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store a conversation."""
        pass
    
    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a specific conversation."""
        pass
    
    @abstractmethod
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get conversations for a user."""
        pass
    
    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a specific conversation."""
        pass
    
    # Conversation summaries
    @abstractmethod
    async def store_conversation_summary(self, summary: ConversationSummary) -> None:
        """Store a conversation summary."""
        pass
    
    @abstractmethod
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries for a user."""
        pass
    
    # User preferences
    @abstractmethod
    async def store_user_preferences(self, preferences: UserPreferences) -> None:
        """Store user preferences."""
        pass
    
    @abstractmethod
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences."""
        pass
    
    # Privacy settings
    @abstractmethod
    async def store_privacy_settings(self, settings: PrivacySettings) -> None:
        """Store privacy settings."""
        pass
    
    @abstractmethod
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings."""
        pass
    
    # Data management
    @abstractmethod
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all data for a user."""
        pass
    
    @abstractmethod
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of all user data."""
        pass
    
    # Health and maintenance
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        pass
    
    @abstractmethod
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data according to retention policies."""
        pass