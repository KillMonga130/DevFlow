"""
Interface definitions for the memory service components.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import (
    Conversation, ConversationContext, SearchQuery, SearchResult,
    DeleteOptions, UserDataExport, PrivacySettings
)


class MemoryServiceInterface(ABC):
    """Interface for the main memory service."""
    
    @abstractmethod
    async def store_conversation(self, user_id: str, conversation: Conversation) -> None:
        """Store a conversation for a user."""
        pass
    
    @abstractmethod
    async def retrieve_context(self, user_id: str, limit: Optional[int] = None) -> ConversationContext:
        """Retrieve conversation context for a user."""
        pass
    
    @abstractmethod
    async def search_history(self, user_id: str, query: SearchQuery) -> List[SearchResult]:
        """Search conversation history."""
        pass
    
    @abstractmethod
    async def delete_user_data(self, user_id: str, options: Optional[DeleteOptions] = None) -> Dict[str, Any]:
        """Delete user data."""
        pass
    
    @abstractmethod
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export user data."""
        pass
    
    @abstractmethod
    async def update_privacy_settings(self, user_id: str, settings: PrivacySettings) -> None:
        """Update privacy settings for a user."""
        pass
    
    @abstractmethod
    async def get_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get privacy settings for a user."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the memory service."""
        pass


class ContextManagerInterface(ABC):
    """Interface for context management."""
    
    @abstractmethod
    async def build_context(self, user_id: str, current_message: str) -> ConversationContext:
        """Build conversation context."""
        pass
    
    @abstractmethod
    async def summarize_conversation(self, conversation: Conversation) -> str:
        """Summarize a conversation."""
        pass
    
    @abstractmethod
    async def update_context(self, user_id: str, conversation: Conversation) -> None:
        """Update context with new conversation."""
        pass
    
    @abstractmethod
    async def prune_old_context(self, user_id: str) -> None:
        """Prune old context data."""
        pass


class PreferenceEngineInterface(ABC):
    """Interface for preference learning and application."""
    
    @abstractmethod
    async def analyze_preferences(self, user_id: str, conversations: List[Conversation]) -> Dict[str, Any]:
        """Analyze user preferences from conversations."""
        pass
    
    @abstractmethod
    async def apply_preferences(self, user_id: str, response: str) -> str:
        """Apply user preferences to a response."""
        pass
    
    @abstractmethod
    async def update_preferences(self, user_id: str, feedback: Dict[str, Any]) -> None:
        """Update preferences based on feedback."""
        pass
    
    @abstractmethod
    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        pass


class PrivacyControllerInterface(ABC):
    """Interface for privacy and data control."""
    
    @abstractmethod
    async def delete_user_data(self, user_id: str, options: DeleteOptions) -> Dict[str, Any]:
        """Delete user data according to options."""
        pass
    
    @abstractmethod
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data."""
        pass
    
    @abstractmethod
    async def apply_retention_policy(self, user_id: str) -> None:
        """Apply data retention policy."""
        pass
    
    @abstractmethod
    async def anonymize_data(self, user_id: str) -> None:
        """Anonymize user data."""
        pass


class SearchServiceInterface(ABC):
    """Interface for search functionality."""
    
    @abstractmethod
    async def search_conversations(self, query: SearchQuery) -> List[SearchResult]:
        """Search conversations."""
        pass
    
    @abstractmethod
    async def index_conversation(self, conversation: Conversation) -> None:
        """Index a conversation for search."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, conversation_id: str) -> None:
        """Remove conversation from search index."""
        pass
    
    @abstractmethod
    async def get_similar_conversations(self, user_id: str, content: str, limit: int = 5) -> List[SearchResult]:
        """Get similar conversations using semantic search."""
        pass


class StorageLayerInterface(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store a conversation."""
        pass
    
    @abstractmethod
    async def retrieve_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        pass
    
    @abstractmethod
    async def retrieve_user_conversations(self, user_id: str, limit: Optional[int] = None) -> List[Conversation]:
        """Retrieve conversations for a user."""
        pass
    
    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation."""
        pass
    
    @abstractmethod
    async def delete_user_conversations(self, user_id: str) -> int:
        """Delete all conversations for a user."""
        pass
    
    @abstractmethod
    async def update_conversation(self, conversation: Conversation) -> None:
        """Update a conversation."""
        pass