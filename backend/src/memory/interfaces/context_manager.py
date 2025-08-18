"""
Context manager interface.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models import (
    ConversationContext, Conversation, ConversationSummary, 
    MessageExchange
)


class ContextManagerInterface(ABC):
    """Interface for conversation context management."""
    
    @abstractmethod
    async def build_context(self, user_id: str, current_message: str) -> ConversationContext:
        """Build conversation context for a user."""
        pass
    
    @abstractmethod
    async def summarize_conversation(self, conversation: Conversation) -> ConversationSummary:
        """Summarize a conversation."""
        pass
    
    @abstractmethod
    async def update_context(self, user_id: str, new_exchange: MessageExchange) -> None:
        """Update context with a new message exchange."""
        pass
    
    @abstractmethod
    async def prune_old_context(self, user_id: str) -> None:
        """Remove old context data to manage memory usage."""
        pass
    
    @abstractmethod
    async def get_relevant_history(self, user_id: str, current_message: str, limit: int = 5) -> List[ConversationSummary]:
        """Get relevant historical context for the current message."""
        pass