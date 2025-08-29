"""
Common data models used across the memory system.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from .conversation import Message


class FeedbackType(str, Enum):
    """Types of user feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    PREFERENCE = "preference"


class MessageExchange(BaseModel):
    """A complete message exchange (user message + assistant response)."""
    user_message: Message
    assistant_message: Message
    exchange_timestamp: datetime = Field(default_factory=datetime.utcnow)
    context_used: Optional[str] = None
    preferences_applied: Optional[Dict[str, Any]] = None
    
    def get_exchange_duration(self) -> float:
        """Get the duration of the exchange in seconds."""
        return (self.assistant_message.timestamp - self.user_message.timestamp).total_seconds()


class UserFeedback(BaseModel):
    """User feedback on system responses."""
    user_id: str = Field(..., min_length=1)
    message_id: str = Field(..., min_length=1)
    feedback_type: FeedbackType
    feedback_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 star rating
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Optional[Dict[str, Any]] = None
    
    def is_positive(self) -> bool:
        """Check if feedback is positive."""
        return self.feedback_type == FeedbackType.POSITIVE or (
            self.rating is not None and self.rating >= 4
        )
    
    def is_correction(self) -> bool:
        """Check if feedback contains a correction."""
        return self.feedback_type == FeedbackType.CORRECTION