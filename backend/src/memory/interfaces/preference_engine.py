"""
Preference engine interface.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models import (
    UserPreferences, Conversation, UserFeedback
)


class PreferenceEngineInterface(ABC):
    """Interface for user preference learning and application."""
    
    @abstractmethod
    async def analyze_user_preferences(self, user_id: str, conversations: List[Conversation]) -> UserPreferences:
        """Analyze conversations to extract user preferences."""
        pass
    
    @abstractmethod
    async def apply_preferences(self, user_id: str, response: str) -> str:
        """Apply user preferences to modify a response."""
        pass
    
    @abstractmethod
    async def update_preferences(self, user_id: str, feedback: UserFeedback) -> None:
        """Update preferences based on user feedback."""
        pass
    
    @abstractmethod
    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get current user preferences."""
        pass
    
    @abstractmethod
    async def learn_from_interaction(self, user_id: str, user_message: str, assistant_response: str, feedback: UserFeedback = None) -> None:
        """Learn preferences from a single interaction."""
        pass