"""
Core conversation data models.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"


class MessageMetadata(BaseModel):
    """Metadata for individual messages."""
    model_config = {"protected_namespaces": ()}
    
    tokens: Optional[int] = None
    processing_time: Optional[float] = None
    model_used: Optional[str] = None
    confidence_score: Optional[float] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @field_validator('tokens')
    @classmethod
    def validate_tokens(cls, v):
        if v is not None and v < 0:
            raise ValueError('Token count cannot be negative')
        return v
    
    @field_validator('processing_time')
    @classmethod
    def validate_processing_time(cls, v):
        if v is not None and v < 0:
            raise ValueError('Processing time cannot be negative')
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageMetadata':
        """Create metadata from dictionary."""
        return cls(**data)


class Message(BaseModel):
    """Individual message in a conversation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        if len(v) > 50000:  # 50KB limit
            raise ValueError('Message content too long (max 50KB)')
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v.tzinfo is None:
            # Convert naive datetime to UTC
            v = v.replace(tzinfo=timezone.utc)
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            'id': self.id,
            'role': self.role.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        # Handle timestamp parsing
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        # Handle metadata
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = MessageMetadata.from_dict(data['metadata'])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_metadata(self, **kwargs) -> None:
        """Update message metadata."""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
            else:
                self.metadata.additional_data[key] = value
        self.metadata.updated_at = datetime.now(timezone.utc)


class ConversationMetadata(BaseModel):
    """Metadata for conversations."""
    total_messages: int = 0
    total_tokens: Optional[int] = None
    duration_seconds: Optional[float] = None
    topics: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    language: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    @field_validator('total_messages')
    @classmethod
    def validate_total_messages(cls, v):
        if v < 0:
            raise ValueError('Total messages cannot be negative')
        return v
    
    @field_validator('total_tokens')
    @classmethod
    def validate_total_tokens(cls, v):
        if v is not None and v < 0:
            raise ValueError('Total tokens cannot be negative')
        return v
    
    @field_validator('duration_seconds')
    @classmethod
    def validate_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError('Duration cannot be negative')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMetadata':
        """Create metadata from dictionary."""
        # Handle datetime parsing
        for field in ['created_at', 'updated_at', 'last_message_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        return cls(**data)
    
    def update_message_stats(self, message_count: int, latest_timestamp: datetime) -> None:
        """Update message statistics."""
        self.total_messages = message_count
        self.last_message_at = latest_timestamp
        self.updated_at = datetime.now(timezone.utc)


class Conversation(BaseModel):
    """Complete conversation data structure."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[Message] = Field(default_factory=list)
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        if len(v) > 255:
            raise ValueError('User ID too long (max 255 characters)')
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v.tzinfo is None:
            # Convert naive datetime to UTC
            v = v.replace(tzinfo=timezone.utc)
        return v
    
    @field_validator('summary')
    @classmethod
    def validate_summary(cls, v):
        if v is not None and len(v) > 5000:
            raise ValueError('Summary too long (max 5000 characters)')
        return v
    
    @model_validator(mode='after')
    def validate_conversation(self):
        """Validate the entire conversation."""
        if self.metadata and self.messages:
            # Ensure metadata matches actual message count
            self.metadata.total_messages = len(self.messages)
            if self.messages:
                self.metadata.last_message_at = self.messages[-1].timestamp
        
        return self
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self._update_metadata()
    
    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to the conversation."""
        self.messages.extend(messages)
        self._update_metadata()
    
    def get_latest_messages(self, count: int = 10) -> List[Message]:
        """Get the latest N messages from the conversation."""
        return self.messages[-count:] if count < len(self.messages) else self.messages
    
    def get_messages_by_role(self, role: MessageRole) -> List[Message]:
        """Get all messages by a specific role."""
        return [msg for msg in self.messages if msg.role == role]
    
    def get_messages_in_range(self, start_time: datetime, end_time: datetime) -> List[Message]:
        """Get messages within a time range."""
        return [
            msg for msg in self.messages 
            if start_time <= msg.timestamp <= end_time
        ]
    
    def calculate_duration(self) -> Optional[float]:
        """Calculate conversation duration in seconds."""
        if len(self.messages) < 2:
            return None
        
        start_time = self.messages[0].timestamp
        end_time = self.messages[-1].timestamp
        duration = (end_time - start_time).total_seconds()
        
        self.metadata.duration_seconds = duration
        return duration
    
    def _update_metadata(self) -> None:
        """Update conversation metadata based on current state."""
        self.metadata.update_message_stats(
            len(self.messages),
            self.messages[-1].timestamp if self.messages else self.timestamp
        )
        
        # Update total tokens if available
        total_tokens = sum(
            msg.metadata.tokens for msg in self.messages 
            if msg.metadata.tokens is not None
        )
        if total_tokens > 0:
            self.metadata.total_tokens = total_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'messages': [msg.to_dict() for msg in self.messages],
            'summary': self.summary,
            'tags': self.tags,
            'metadata': self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create conversation from dictionary."""
        # Handle timestamp parsing
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        # Handle messages
        if 'messages' in data:
            data['messages'] = [
                Message.from_dict(msg_data) if isinstance(msg_data, dict) else msg_data
                for msg_data in data['messages']
            ]
        
        # Handle metadata
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = ConversationMetadata.from_dict(data['metadata'])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert conversation to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Conversation':
        """Create conversation from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def clone(self) -> 'Conversation':
        """Create a deep copy of the conversation."""
        data = self.to_dict()
        # Generate new ID for the clone
        data['id'] = str(uuid.uuid4())
        return self.from_dict(data)
    
    def merge_with(self, other: 'Conversation') -> 'Conversation':
        """Merge this conversation with another conversation."""
        if self.user_id != other.user_id:
            raise ValueError("Cannot merge conversations from different users")
        
        # Create new conversation with combined messages
        all_messages = self.messages + other.messages
        # Sort by timestamp
        all_messages.sort(key=lambda msg: msg.timestamp)
        
        # Create merged conversation
        merged = Conversation(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            timestamp=min(self.timestamp, other.timestamp),
            messages=all_messages,
            tags=list(set(self.tags + other.tags))
        )
        
        return merged