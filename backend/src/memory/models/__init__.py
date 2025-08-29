"""
Core data models for the conversational memory system.
"""

from .conversation import Conversation, Message, ConversationMetadata, MessageMetadata, MessageRole
from .context import ConversationContext, ConversationSummary
from .preferences import UserPreferences, ResponseStyle, TopicInterest, CommunicationPreferences
from .search import SearchQuery, SearchResult, DateRange
from .privacy import (
    PrivacySettings, DeleteOptions, UserDataExport, 
    DataRetentionPolicy, PrivacyMode, DeleteScope
)
from .common import MessageExchange, UserFeedback

__all__ = [
    "Conversation",
    "Message", 
    "MessageRole",
    "ConversationMetadata",
    "MessageMetadata",
    "ConversationContext",
    "ConversationSummary",
    "UserPreferences",
    "ResponseStyle",
    "TopicInterest", 
    "CommunicationPreferences",
    "SearchQuery",
    "SearchResult",
    "DateRange",
    "PrivacySettings",
    "DeleteOptions",
    "UserDataExport",
    "DataRetentionPolicy",
    "PrivacyMode", 
    "DeleteScope",
    "MessageExchange",
    "UserFeedback"
]