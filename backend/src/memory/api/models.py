"""
API request and response models for the memory service.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models import (
    Conversation, ConversationContext, SearchQuery, SearchResult,
    DeleteOptions, UserDataExport, PrivacySettings, MessageRole
)


# Request Models
class StoreConversationRequest(BaseModel):
    """Request model for storing a conversation."""
    conversation: Conversation


class RetrieveContextRequest(BaseModel):
    """Request model for retrieving context."""
    user_id: str = Field(..., min_length=1)
    limit: Optional[int] = Field(default=None, ge=1, le=100)


class SearchHistoryRequest(BaseModel):
    """Request model for searching conversation history."""
    user_id: str
    keywords: Optional[List[str]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    topics: Optional[List[str]] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_context: bool = True
    semantic_search: bool = False
    
    def to_search_query(self) -> SearchQuery:
        """Convert to SearchQuery model."""
        from ..models.search import DateRange
        
        date_range = None
        if self.date_range_start or self.date_range_end:
            date_range = DateRange(
                start_date=self.date_range_start,
                end_date=self.date_range_end
            )
        
        return SearchQuery(
            user_id=self.user_id,
            keywords=self.keywords,
            date_range=date_range,
            topics=self.topics,
            limit=self.limit,
            offset=self.offset,
            include_context=self.include_context,
            semantic_search=self.semantic_search
        )


class DeleteUserDataRequest(BaseModel):
    """Request model for deleting user data."""
    user_id: str
    delete_conversations: bool = True
    delete_preferences: bool = True
    delete_search_history: bool = True
    conversation_ids: Optional[List[str]] = None
    before_date: Optional[datetime] = None
    
    def to_delete_options(self) -> DeleteOptions:
        """Convert to DeleteOptions model."""
        from ..models.privacy import DeleteScope
        
        # Determine scope based on what's being deleted
        if self.conversation_ids:
            scope = DeleteScope.SPECIFIC_CONVERSATIONS
        elif self.before_date:
            scope = DeleteScope.DATE_RANGE
        elif self.delete_conversations and self.delete_preferences and self.delete_search_history:
            scope = DeleteScope.ALL_DATA
        elif self.delete_conversations:
            scope = DeleteScope.CONVERSATIONS
        elif self.delete_preferences:
            scope = DeleteScope.PREFERENCES
        elif self.delete_search_history:
            scope = DeleteScope.SEARCH_HISTORY
        else:
            scope = DeleteScope.ALL_DATA
        
        return DeleteOptions(
            scope=scope,
            conversation_ids=self.conversation_ids,
            date_range_start=self.before_date,
            date_range_end=None,
            confirm_deletion=True
        )


class ExportUserDataRequest(BaseModel):
    """Request model for exporting user data."""
    user_id: str
    format: str = Field(default="json", pattern="^(json|csv|yaml)$")
    include_conversations: bool = True
    include_preferences: bool = True
    include_search_history: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class UpdatePrivacySettingsRequest(BaseModel):
    """Request model for updating privacy settings."""
    user_id: str
    privacy_settings: PrivacySettings


# Response Models
class StoreConversationResponse(BaseModel):
    """Response model for storing a conversation."""
    success: bool
    message: str
    conversation_id: str


class RetrieveContextResponse(BaseModel):
    """Response model for retrieving context."""
    success: bool
    context: Optional[ConversationContext] = None
    message: str = ""


class SearchHistoryResponse(BaseModel):
    """Response model for searching conversation history."""
    success: bool
    results: List[SearchResult] = Field(default_factory=list)
    total_count: int = 0
    has_more: bool = False
    message: str = ""


class DeleteUserDataResponse(BaseModel):
    """Response model for deleting user data."""
    success: bool
    message: str
    deleted_conversations: int = 0
    deleted_preferences: bool = False
    deleted_search_history: bool = False


class ExportUserDataResponse(BaseModel):
    """Response model for exporting user data."""
    success: bool
    export_data: Optional[UserDataExport] = None
    download_url: Optional[str] = None
    message: str = ""


class UpdatePrivacySettingsResponse(BaseModel):
    """Response model for updating privacy settings."""
    success: bool
    message: str


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    components: Dict[str, str] = Field(default_factory=dict)
    initialized: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error_code: Optional[str] = None
    error_message: str
    details: Optional[Dict[str, Any]] = None


# Utility models for chat integration
class ChatMessage(BaseModel):
    """Simple chat message model for API integration."""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Enhanced chat request with memory integration."""
    user_id: str
    message: str
    include_context: bool = True
    context_limit: Optional[int] = None


class ChatResponse(BaseModel):
    """Enhanced chat response with memory integration."""
    reply: str
    context_used: bool = False
    context_summary: Optional[str] = None
    conversation_id: Optional[str] = None