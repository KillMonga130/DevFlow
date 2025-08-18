"""
User preference data models.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ResponseStyleType(str, Enum):
    """Response style preferences."""
    CONCISE = "concise"
    DETAILED = "detailed"
    CONVERSATIONAL = "conversational"
    TECHNICAL = "technical"
    CASUAL = "casual"
    FORMAL = "formal"


class CommunicationTone(str, Enum):
    """Communication tone preferences."""
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    HELPFUL = "helpful"
    DIRECT = "direct"
    ENCOURAGING = "encouraging"


class ResponseStyle(BaseModel):
    """User's preferred response style."""
    style_type: ResponseStyleType = ResponseStyleType.CONVERSATIONAL
    tone: CommunicationTone = CommunicationTone.HELPFUL
    preferred_length: Optional[str] = None  # "short", "medium", "long"
    include_examples: bool = True
    include_explanations: bool = True
    confidence: float = 0.0  # How confident we are in this preference
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @field_validator('preferred_length')
    @classmethod
    def validate_preferred_length(cls, v):
        if v is not None and v not in ["short", "medium", "long"]:
            raise ValueError('Preferred length must be "short", "medium", or "long"')
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response style to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResponseStyle':
        """Create response style from dictionary."""
        # Handle datetime parsing
        for field in ['created_at', 'updated_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        return cls(**data)
    
    def update_confidence(self, new_confidence: float) -> None:
        """Update confidence level."""
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.updated_at = datetime.now(timezone.utc)


class TopicInterest(BaseModel):
    """User's interest in specific topics."""
    topic: str
    interest_level: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    frequency_mentioned: int = 0
    last_mentioned: Optional[datetime] = None
    context_keywords: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v):
        if not v or not v.strip():
            raise ValueError('Topic cannot be empty')
        if len(v) > 200:
            raise ValueError('Topic name too long (max 200 characters)')
        return v.strip()
    
    @field_validator('frequency_mentioned')
    @classmethod
    def validate_frequency(cls, v):
        if v < 0:
            raise ValueError('Frequency mentioned cannot be negative')
        return v
    
    @field_validator('last_mentioned')
    @classmethod
    def validate_last_mentioned(cls, v):
        if v and v.tzinfo is None:
            # Convert naive datetime to UTC
            v = v.replace(tzinfo=timezone.utc)
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert topic interest to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicInterest':
        """Create topic interest from dictionary."""
        # Handle datetime parsing
        for field in ['last_mentioned', 'created_at', 'updated_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        return cls(**data)
    
    def increment_frequency(self) -> None:
        """Increment frequency and update timestamp."""
        self.frequency_mentioned += 1
        self.last_mentioned = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_interest_level(self, new_level: float) -> None:
        """Update interest level with validation."""
        if not (0.0 <= new_level <= 1.0):
            raise ValueError('Interest level must be between 0.0 and 1.0')
        self.interest_level = new_level
        self.updated_at = datetime.now(timezone.utc)


class CommunicationPreferences(BaseModel):
    """User's communication preferences."""
    prefers_step_by_step: bool = False
    prefers_code_examples: bool = True
    prefers_analogies: bool = False
    prefers_bullet_points: bool = False
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @field_validator('language_preference')
    @classmethod
    def validate_language_preference(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError('Language preference code too long (max 10 characters)')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError('Timezone string too long (max 50 characters)')
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert communication preferences to dictionary for serialization."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommunicationPreferences':
        """Create communication preferences from dictionary."""
        # Handle datetime parsing
        for field in ['created_at', 'updated_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        return cls(**data)
    
    def update_preference(self, preference_name: str, value: Any) -> None:
        """Update a specific preference."""
        if hasattr(self, preference_name):
            setattr(self, preference_name, value)
            self.updated_at = datetime.now(timezone.utc)
        else:
            raise ValueError(f"Unknown preference: {preference_name}")
    
    def get_preference_summary(self) -> Dict[str, Any]:
        """Get a summary of communication preferences."""
        return {
            'formatting': {
                'step_by_step': self.prefers_step_by_step,
                'code_examples': self.prefers_code_examples,
                'analogies': self.prefers_analogies,
                'bullet_points': self.prefers_bullet_points
            },
            'localization': {
                'language': self.language_preference,
                'timezone': self.timezone
            },
            'confidence': self.confidence
        }


class UserPreferences(BaseModel):
    """Complete user preference profile."""
    user_id: str
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)
    topic_interests: List[TopicInterest] = Field(default_factory=list)
    communication_preferences: CommunicationPreferences = Field(default_factory=CommunicationPreferences)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    learning_enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1  # For schema versioning
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        if len(v) > 255:
            raise ValueError('User ID too long (max 255 characters)')
        return v
    
    @field_validator('last_updated', 'created_at')
    @classmethod
    def validate_timestamps(cls, v):
        if v.tzinfo is None:
            # Convert naive datetime to UTC
            v = v.replace(tzinfo=timezone.utc)
        return v
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        if v < 1:
            raise ValueError('Version must be positive')
        return v
    
    @model_validator(mode='after')
    def validate_preferences(self):
        """Validate the entire preferences object."""
        # Ensure no duplicate topics
        topics = [interest.topic.lower() for interest in self.topic_interests]
        if len(topics) != len(set(topics)):
            raise ValueError('Duplicate topics found in interests')
        
        return self
    
    def get_topic_interest(self, topic: str) -> Optional[TopicInterest]:
        """Get interest level for a specific topic."""
        for interest in self.topic_interests:
            if interest.topic.lower() == topic.lower():
                return interest
        return None
    
    def add_or_update_topic_interest(self, topic: str, interest_level: float, keywords: Optional[List[str]] = None) -> None:
        """Add or update interest in a topic."""
        existing = self.get_topic_interest(topic)
        if existing:
            existing.update_interest_level(interest_level)
            existing.increment_frequency()
            if keywords:
                # Merge keywords, keeping unique ones
                existing.context_keywords = list(set(existing.context_keywords + keywords))
        else:
            self.topic_interests.append(TopicInterest(
                topic=topic,
                interest_level=interest_level,
                frequency_mentioned=1,
                last_mentioned=datetime.now(timezone.utc),
                context_keywords=keywords or []
            ))
        self.last_updated = datetime.now(timezone.utc)
    
    def remove_topic_interest(self, topic: str) -> bool:
        """Remove a topic interest."""
        for i, interest in enumerate(self.topic_interests):
            if interest.topic.lower() == topic.lower():
                del self.topic_interests[i]
                self.last_updated = datetime.now(timezone.utc)
                return True
        return False
    
    def get_top_interests(self, limit: int = 10) -> List[TopicInterest]:
        """Get top interests sorted by interest level and frequency."""
        return sorted(
            self.topic_interests,
            key=lambda x: (x.interest_level, x.frequency_mentioned),
            reverse=True
        )[:limit]
    
    def update_response_style(self, **kwargs) -> None:
        """Update response style preferences."""
        for key, value in kwargs.items():
            if hasattr(self.response_style, key):
                setattr(self.response_style, key, value)
        self.response_style.updated_at = datetime.now(timezone.utc)
        self.last_updated = datetime.now(timezone.utc)
    
    def update_communication_preferences(self, **kwargs) -> None:
        """Update communication preferences."""
        for key, value in kwargs.items():
            self.communication_preferences.update_preference(key, value)
        self.last_updated = datetime.now(timezone.utc)
    
    def get_preference_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all preferences."""
        return {
            'user_id': self.user_id,
            'response_style': {
                'style_type': self.response_style.style_type.value,
                'tone': self.response_style.tone.value,
                'preferred_length': self.response_style.preferred_length,
                'confidence': self.response_style.confidence
            },
            'communication': self.communication_preferences.get_preference_summary(),
            'top_interests': [
                {
                    'topic': interest.topic,
                    'level': interest.interest_level,
                    'frequency': interest.frequency_mentioned
                }
                for interest in self.get_top_interests(5)
            ],
            'learning_enabled': self.learning_enabled,
            'last_updated': self.last_updated.isoformat(),
            'version': self.version
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user preferences to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'response_style': self.response_style.to_dict(),
            'topic_interests': [interest.to_dict() for interest in self.topic_interests],
            'communication_preferences': self.communication_preferences.to_dict(),
            'last_updated': self.last_updated.isoformat(),
            'learning_enabled': self.learning_enabled,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create user preferences from dictionary."""
        # Handle datetime parsing
        for field in ['last_updated', 'created_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
        
        # Handle nested objects
        if 'response_style' in data and isinstance(data['response_style'], dict):
            data['response_style'] = ResponseStyle.from_dict(data['response_style'])
        
        if 'topic_interests' in data:
            data['topic_interests'] = [
                TopicInterest.from_dict(interest_data) if isinstance(interest_data, dict) else interest_data
                for interest_data in data['topic_interests']
            ]
        
        if 'communication_preferences' in data and isinstance(data['communication_preferences'], dict):
            data['communication_preferences'] = CommunicationPreferences.from_dict(data['communication_preferences'])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert user preferences to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UserPreferences':
        """Create user preferences from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def clone(self) -> 'UserPreferences':
        """Create a deep copy of the user preferences."""
        return self.from_dict(self.to_dict())
    
    def merge_with(self, other: 'UserPreferences') -> 'UserPreferences':
        """Merge this preferences with another preferences object."""
        if self.user_id != other.user_id:
            raise ValueError("Cannot merge preferences from different users")
        
        # Create merged preferences starting with self
        merged = self.clone()
        
        # Merge topic interests
        for other_interest in other.topic_interests:
            existing = merged.get_topic_interest(other_interest.topic)
            if existing:
                # Average the interest levels and sum frequencies
                new_level = (existing.interest_level + other_interest.interest_level) / 2
                existing.update_interest_level(new_level)
                existing.frequency_mentioned += other_interest.frequency_mentioned
                # Use the more recent timestamp
                if other_interest.last_mentioned and (
                    not existing.last_mentioned or 
                    other_interest.last_mentioned > existing.last_mentioned
                ):
                    existing.last_mentioned = other_interest.last_mentioned
                # Merge keywords
                existing.context_keywords = list(set(existing.context_keywords + other_interest.context_keywords))
            else:
                merged.topic_interests.append(other_interest)
        
        # Use the more recent timestamps and higher confidence values
        if other.response_style.confidence > merged.response_style.confidence:
            merged.response_style = other.response_style
        
        if other.communication_preferences.confidence > merged.communication_preferences.confidence:
            merged.communication_preferences = other.communication_preferences
        
        # Use the most recent update time
        merged.last_updated = max(self.last_updated, other.last_updated)
        
        return merged