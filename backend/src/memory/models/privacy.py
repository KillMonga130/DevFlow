"""
Privacy and data control models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DataRetentionPolicy(str, Enum):
    """Data retention policy options."""
    INDEFINITE = "indefinite"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    DAYS_365 = "365_days"
    SESSION_ONLY = "session_only"


class PrivacyMode(str, Enum):
    """Privacy mode settings."""
    FULL_MEMORY = "full_memory"
    LIMITED_MEMORY = "limited_memory"
    NO_MEMORY = "no_memory"


class DeleteScope(str, Enum):
    """Scope of data deletion."""
    ALL_DATA = "all_data"
    CONVERSATIONS = "conversations"
    PREFERENCES = "preferences"
    SEARCH_HISTORY = "search_history"
    SPECIFIC_CONVERSATIONS = "specific_conversations"
    DATE_RANGE = "date_range"


class PrivacySettings(BaseModel):
    """User privacy settings."""
    user_id: str
    privacy_mode: PrivacyMode = PrivacyMode.FULL_MEMORY
    data_retention_policy: DataRetentionPolicy = DataRetentionPolicy.DAYS_90
    allow_preference_learning: bool = True
    allow_search_indexing: bool = True
    encrypt_sensitive_data: bool = True
    share_analytics: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def is_memory_enabled(self) -> bool:
        """Check if memory functionality is enabled."""
        return self.privacy_mode != PrivacyMode.NO_MEMORY
    
    def allows_long_term_storage(self) -> bool:
        """Check if long-term storage is allowed."""
        return self.data_retention_policy != DataRetentionPolicy.SESSION_ONLY


class DeleteOptions(BaseModel):
    """Options for data deletion requests."""
    scope: DeleteScope
    conversation_ids: Optional[List[str]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    confirm_deletion: bool = False
    reason: Optional[str] = None


class UserDataExport(BaseModel):
    """Complete user data export."""
    user_id: str
    export_timestamp: datetime = Field(default_factory=datetime.utcnow)
    conversations: List[Dict[str, Any]] = Field(default_factory=list)
    preferences: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None
    search_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_export_size(self) -> Dict[str, int]:
        """Get size statistics for the export."""
        return {
            "total_conversations": len(self.conversations),
            "total_messages": sum(
                len(conv.get("messages", [])) for conv in self.conversations
            ),
            "has_preferences": self.preferences is not None,
            "search_history_entries": len(self.search_history)
        }