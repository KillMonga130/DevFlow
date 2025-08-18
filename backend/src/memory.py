"""
Main entry point for the conversational memory system.

This module provides a simplified interface to the memory system for integration
with the existing chat application.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from .memory.services import MemoryService
from .memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    SearchQuery, UserPreferences, PrivacySettings
)
from .memory.config import get_memory_config


class ConversationalMemory:
    """Main interface for the conversational memory system."""
    
    def __init__(self):
        """Initialize the conversational memory system."""
        self.config = get_memory_config()
        self.memory_service = MemoryService()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the memory system."""
        if self._initialized:
            return
        
        # Initialize services and connections
        # This will be implemented in later tasks
        self._initialized = True
    
    async def store_message(self, user_id: str, user_message: str, assistant_response: str) -> str:
        """Store a message exchange and return conversation ID."""
        if not self._initialized:
            await self.initialize()
        
        # Create conversation if needed
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Create messages
        user_msg = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=user_message,
            timestamp=timestamp
        )
        
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=assistant_response,
            timestamp=timestamp
        )
        
        # Create conversation
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            timestamp=timestamp,
            messages=[user_msg, assistant_msg]
        )
        
        # Store conversation
        await self.memory_service.store_conversation(user_id, conversation)
        
        return conversation_id
    
    async def get_context(self, user_id: str, current_message: str = "") -> Dict[str, Any]:
        """Get conversation context for a user."""
        if not self._initialized:
            await self.initialize()
        
        context = await self.memory_service.retrieve_context(user_id)
        
        return {
            "user_id": context.user_id,
            "recent_messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in context.recent_messages
            ],
            "context_summary": context.context_summary,
            "has_preferences": context.user_preferences is not None
        }
    
    async def search_history(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search through conversation history."""
        if not self._initialized:
            await self.initialize()
        
        search_query = SearchQuery(
            keywords=[query] if query else None,
            user_id=user_id,
            limit=limit
        )
        
        results = await self.memory_service.search_history(user_id, search_query)
        
        return [
            {
                "conversation_id": result.conversation_id,
                "relevance_score": result.relevance_score,
                "timestamp": result.timestamp.isoformat(),
                "content_snippet": result.content_snippet,
                "topics": result.topics
            }
            for result in results
        ]
    
    async def delete_user_data(self, user_id: str) -> None:
        """Delete all data for a user."""
        if not self._initialized:
            await self.initialize()
        
        await self.memory_service.delete_user_data(user_id)
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all user data."""
        if not self._initialized:
            await self.initialize()
        
        export_data = await self.memory_service.export_user_data(user_id)
        
        return {
            "user_id": export_data.user_id,
            "export_timestamp": export_data.export_timestamp.isoformat(),
            "conversations": export_data.conversations,
            "preferences": export_data.preferences,
            "privacy_settings": export_data.privacy_settings,
            "export_size": export_data.get_export_size()
        }


# Global instance
_memory_instance: Optional[ConversationalMemory] = None


def get_memory_system() -> ConversationalMemory:
    """Get the global memory system instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationalMemory()
    return _memory_instance