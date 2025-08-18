"""
Validation utilities for the memory system.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ..models import (
    Conversation, Message, ConversationContext, UserPreferences,
    SearchQuery, PrivacySettings, MessageRole
)


def validate_user_id(user_id: str) -> bool:
    """Validate user ID format."""
    if not user_id or not isinstance(user_id, str):
        return False
    
    # Basic validation - alphanumeric with hyphens and underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, user_id)) and len(user_id) <= 255


def validate_conversation_data(conversation: Conversation) -> Dict[str, Any]:
    """Validate conversation data and return validation results."""
    errors = []
    warnings = []
    
    # Validate basic fields
    if not conversation.id:
        errors.append("Conversation ID is required")
    
    if not validate_user_id(conversation.user_id):
        errors.append("Invalid user ID format")
    
    if not conversation.messages:
        warnings.append("Conversation has no messages")
    
    # Validate messages
    for i, message in enumerate(conversation.messages):
        if not message.id:
            errors.append(f"Message {i} missing ID")
        
        if not message.content.strip():
            warnings.append(f"Message {i} has empty content")
        
        if len(message.content) > 10000:  # 10KB limit per message
            warnings.append(f"Message {i} content is very long ({len(message.content)} chars)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_message_content(content: str) -> bool:
    """Validate message content."""
    if not content or not isinstance(content, str):
        return False
    
    # Check for reasonable length limits
    if len(content.strip()) == 0 or len(content) > 50000:  # 50KB limit
        return False
    
    return True


def validate_message(message: Message) -> Dict[str, Any]:
    """Validate a complete message object."""
    errors = []
    warnings = []
    
    # Validate ID
    if not message.id or not isinstance(message.id, str):
        errors.append("Message ID is required and must be a string")
    elif len(message.id) > 255:
        errors.append("Message ID is too long (max 255 characters)")
    
    # Validate role
    if not isinstance(message.role, MessageRole):
        errors.append("Message role must be a valid MessageRole enum")
    
    # Validate content
    if not validate_message_content(message.content):
        errors.append("Message content is invalid")
    
    # Validate timestamp
    if not isinstance(message.timestamp, datetime):
        errors.append("Message timestamp must be a datetime object")
    elif message.timestamp > datetime.now(timezone.utc):
        warnings.append("Message timestamp is in the future")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_conversation_context(context: ConversationContext) -> Dict[str, Any]:
    """Validate conversation context data."""
    errors = []
    warnings = []
    
    # Validate user ID
    if not validate_user_id(context.user_id):
        errors.append("Invalid user ID in conversation context")
    
    # Validate recent messages
    for i, message in enumerate(context.recent_messages):
        message_validation = validate_message(message)
        if not message_validation["valid"]:
            errors.extend([f"Recent message {i}: {error}" for error in message_validation["errors"]])
    
    # Check context size
    if len(context.recent_messages) > 100:
        warnings.append("Context has many recent messages, may impact performance")
    
    # Validate context summary
    if context.context_summary and len(context.context_summary) > 5000:
        warnings.append("Context summary is very long")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_user_preferences(preferences: UserPreferences) -> Dict[str, Any]:
    """Validate user preferences data."""
    errors = []
    warnings = []
    
    # Validate user ID
    if not validate_user_id(preferences.user_id):
        errors.append("Invalid user ID in preferences")
    
    # Validate topic interests
    for i, interest in enumerate(preferences.topic_interests):
        if not interest.topic or not isinstance(interest.topic, str):
            errors.append(f"Topic interest {i}: topic name is required")
        
        if not (0.0 <= interest.interest_level <= 1.0):
            errors.append(f"Topic interest {i}: interest level must be between 0.0 and 1.0")
        
        if interest.frequency_mentioned < 0:
            errors.append(f"Topic interest {i}: frequency mentioned cannot be negative")
    
    # Check for duplicate topics
    topics = [interest.topic.lower() for interest in preferences.topic_interests]
    if len(topics) != len(set(topics)):
        warnings.append("Duplicate topics found in preferences")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_search_query(query: SearchQuery) -> Dict[str, Any]:
    """Validate search query parameters."""
    errors = []
    warnings = []
    
    # Validate user ID
    if not validate_user_id(query.user_id):
        errors.append("Invalid user ID in search query")
    
    # Validate limit and offset
    if query.limit <= 0 or query.limit > 1000:
        errors.append("Search limit must be between 1 and 1000")
    
    if query.offset < 0:
        errors.append("Search offset cannot be negative")
    
    # Validate keywords
    if query.keywords:
        for keyword in query.keywords:
            if not keyword or not isinstance(keyword, str):
                errors.append("All keywords must be non-empty strings")
            elif len(keyword) > 100:
                warnings.append(f"Keyword '{keyword}' is very long")
    
    # Validate date range
    if query.date_range:
        if (query.date_range.start_date and query.date_range.end_date and 
            query.date_range.start_date > query.date_range.end_date):
            errors.append("Search date range start must be before end")
    
    # Check if query has any search criteria
    if not query.has_filters():
        warnings.append("Search query has no filters, may return many results")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_privacy_settings(settings: PrivacySettings) -> Dict[str, Any]:
    """Validate privacy settings."""
    errors = []
    warnings = []
    
    # Validate user ID
    if not validate_user_id(settings.user_id):
        errors.append("Invalid user ID in privacy settings")
    
    # Validate timestamp
    if not isinstance(settings.last_updated, datetime):
        errors.append("Privacy settings last_updated must be a datetime object")
    
    # Check for conflicting settings
    if not settings.is_memory_enabled() and settings.allow_preference_learning:
        warnings.append("Preference learning enabled but memory is disabled")
    
    if not settings.allows_long_term_storage() and settings.allow_search_indexing:
        warnings.append("Search indexing enabled but long-term storage is disabled")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, errors: List[str], warnings: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors
        self.warnings = warnings or []


def validate_and_raise(validation_result: Dict[str, Any], context: str = "Data validation") -> None:
    """Validate a result and raise ValidationError if invalid."""
    if not validation_result["valid"]:
        raise ValidationError(
            f"{context} failed",
            validation_result["errors"],
            validation_result.get("warnings", [])
        )