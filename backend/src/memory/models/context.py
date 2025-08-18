"""
Context management data models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .conversation import Message
from .preferences import UserPreferences


class ConversationSummary(BaseModel):
    """Summary of a conversation for context building."""
    conversation_id: str
    timestamp: datetime
    summary_text: str
    key_topics: List[str] = Field(default_factory=list)
    importance_score: float = 0.0
    message_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    """Context information for current conversation."""
    user_id: str
    recent_messages: List[Message] = Field(default_factory=list)
    relevant_history: List[ConversationSummary] = Field(default_factory=list)
    user_preferences: Optional[UserPreferences] = None
    context_summary: str = ""
    total_context_tokens: Optional[int] = None
    context_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def add_recent_message(self, message: Message) -> None:
        """Add a message to recent context."""
        self.recent_messages.append(message)
    
    def get_context_text(self) -> str:
        """Generate a text representation of the context."""
        context_parts = []
        
        if self.context_summary:
            context_parts.append(f"Context Summary: {self.context_summary}")
        
        if self.relevant_history:
            history_text = "\n".join([
                f"- {summary.summary_text} (Topics: {', '.join(summary.key_topics)})"
                for summary in self.relevant_history
            ])
            context_parts.append(f"Relevant History:\n{history_text}")
        
        if self.recent_messages:
            recent_text = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in self.recent_messages[-5:]  # Last 5 messages
            ])
            context_parts.append(f"Recent Messages:\n{recent_text}")
        
        return "\n\n".join(context_parts)