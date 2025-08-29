"""
Data integrity service for handling data corruption, validation, and recovery.
"""

import hashlib
import json
import logging
import pickle
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from ..models import (
    Conversation, Message, ConversationSummary, UserPreferences,
    ConversationContext
)
from ..utils.validation import ValidationError

logger = logging.getLogger(__name__)


class DataCorruptionError(Exception):
    """Exception raised when data corruption is detected."""
    pass


# Alias for backward compatibility
CorruptionError = DataCorruptionError


class DataIntegrityService:
    """
    Service for handling data integrity, corruption detection, and recovery.
    """
    
    def __init__(self):
        """Initialize the data integrity service."""
        self._corruption_log: List[Dict[str, Any]] = []
        self._quarantine_storage: Dict[str, Any] = {}
        self._backup_storage: Dict[str, Any] = {}
        self._integrity_checks_enabled = True
        
    def enable_integrity_checks(self, enabled: bool = True) -> None:
        """Enable or disable integrity checks."""
        self._integrity_checks_enabled = enabled
        logger.info(f"Data integrity checks {'enabled' if enabled else 'disabled'}")
    
    def generate_checksum(self, data: Any) -> str:
        """Alias for calculate_checksum for backward compatibility."""
        return self.calculate_checksum(data)
    
    def calculate_checksum(self, data: Any) -> str:
        """
        Calculate a checksum for data integrity verification.
        
        Args:
            data: The data to calculate checksum for
            
        Returns:
            Hexadecimal checksum string
        """
        try:
            # Convert data to a consistent string representation
            if hasattr(data, 'model_dump'):
                # For Pydantic models
                data_dict = data.model_dump()
                data_str = json.dumps(data_dict, sort_keys=True, default=str)
            elif hasattr(data, '__dict__'):
                # For objects with attributes
                data_dict = asdict(data) if hasattr(data, '__dataclass_fields__') else data.__dict__
                data_str = json.dumps(data_dict, sort_keys=True, default=str)
            elif isinstance(data, (dict, list)):
                # For dictionaries and lists
                data_str = json.dumps(data, sort_keys=True, default=str)
            else:
                # For primitive types
                data_str = str(data)
            
            # Calculate SHA-256 hash
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""
    
    def validate_data_integrity(self, data: Any, expected_checksum: str) -> None:
        """
        Validate data integrity using checksum, raising exception if corrupted.
        
        Args:
            data: The data to verify
            expected_checksum: The expected checksum
            
        Raises:
            DataCorruptionError: If data integrity check fails
        """
        if not expected_checksum or len(expected_checksum) != 64:
            raise DataCorruptionError("Invalid checksum format")
        
        if not self.verify_checksum(data, expected_checksum):
            raise DataCorruptionError("Data corruption detected - checksum mismatch")
    
    def verify_checksum(self, data: Any, expected_checksum: str) -> bool:
        """
        Verify data integrity using checksum.
        
        Args:
            data: The data to verify
            expected_checksum: The expected checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        if not self._integrity_checks_enabled:
            return True
        
        try:
            actual_checksum = self.calculate_checksum(data)
            return actual_checksum == expected_checksum
        except Exception as e:
            logger.error(f"Error verifying checksum: {e}")
            return False
    
    def validate_conversation(self, conversation: Conversation) -> Tuple[bool, List[str]]:
        """
        Validate a conversation for data integrity.
        
        Args:
            conversation: The conversation to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Basic structure validation
            if not conversation.id:
                errors.append("Conversation ID is missing")
            
            if not conversation.user_id:
                errors.append("User ID is missing")
            
            if not conversation.timestamp:
                errors.append("Timestamp is missing")
            elif not isinstance(conversation.timestamp, datetime):
                errors.append("Timestamp is not a datetime object")
            
            # Messages validation
            if not isinstance(conversation.messages, list):
                errors.append("Messages is not a list")
            else:
                for i, message in enumerate(conversation.messages):
                    msg_errors = self._validate_message(message, f"Message {i}")
                    errors.extend(msg_errors)
            
            # Metadata validation
            if hasattr(conversation, 'metadata') and conversation.metadata:
                if hasattr(conversation.metadata, 'total_tokens') and conversation.metadata.total_tokens is not None:
                    if not isinstance(conversation.metadata.total_tokens, int) or conversation.metadata.total_tokens < 0:
                        errors.append("Invalid total_tokens in metadata")
                
                if hasattr(conversation.metadata, 'duration_seconds') and conversation.metadata.duration_seconds is not None:
                    if not isinstance(conversation.metadata.duration_seconds, (int, float)) or conversation.metadata.duration_seconds < 0:
                        errors.append("Invalid duration_seconds in metadata")
            
            # Logical consistency checks
            if conversation.messages:
                # Check message timestamps are in order
                for i in range(1, len(conversation.messages)):
                    if conversation.messages[i].timestamp < conversation.messages[i-1].timestamp:
                        errors.append(f"Message timestamps are not in chronological order at index {i}")
                
                # Check conversation timestamp is reasonable relative to messages
                first_msg_time = conversation.messages[0].timestamp
                last_msg_time = conversation.messages[-1].timestamp
                
                if conversation.timestamp < first_msg_time or conversation.timestamp > last_msg_time + timedelta(hours=1):
                    errors.append("Conversation timestamp is inconsistent with message timestamps")
            
        except Exception as e:
            errors.append(f"Exception during validation: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_message(self, message: Message, context: str = "Message") -> List[str]:
        """Validate a single message."""
        errors = []
        
        try:
            if not message.id:
                errors.append(f"{context}: ID is missing")
            
            if not message.role:
                errors.append(f"{context}: Role is missing")
            elif message.role not in ['user', 'assistant', 'system']:
                errors.append(f"{context}: Invalid role '{message.role}'")
            
            if not message.content:
                errors.append(f"{context}: Content is missing")
            elif not isinstance(message.content, str):
                errors.append(f"{context}: Content is not a string")
            elif len(message.content.strip()) == 0:
                errors.append(f"{context}: Content is empty")
            
            if not message.timestamp:
                errors.append(f"{context}: Timestamp is missing")
            elif not isinstance(message.timestamp, datetime):
                errors.append(f"{context}: Timestamp is not a datetime object")
            
            # Content length validation
            if isinstance(message.content, str) and len(message.content) > 100000:  # 100KB limit
                errors.append(f"{context}: Content exceeds maximum length")
            
        except Exception as e:
            errors.append(f"{context}: Exception during validation: {str(e)}")
        
        return errors
    
    def validate_conversation_summary(self, summary: ConversationSummary) -> Tuple[bool, List[str]]:
        """
        Validate a conversation summary for data integrity.
        
        Args:
            summary: The conversation summary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if not summary.conversation_id:
                errors.append("Conversation ID is missing")
            
            if not summary.timestamp:
                errors.append("Timestamp is missing")
            elif not isinstance(summary.timestamp, datetime):
                errors.append("Timestamp is not a datetime object")
            
            if not summary.summary_text:
                errors.append("Summary text is missing")
            elif not isinstance(summary.summary_text, str):
                errors.append("Summary text is not a string")
            
            if summary.message_count is not None:
                if not isinstance(summary.message_count, int) or summary.message_count < 0:
                    errors.append("Invalid message count")
            
            if summary.importance_score is not None:
                if not isinstance(summary.importance_score, (int, float)) or not (0 <= summary.importance_score <= 1):
                    errors.append("Invalid importance score (must be between 0 and 1)")
            
            if summary.key_topics is not None:
                if not isinstance(summary.key_topics, list):
                    errors.append("Key topics is not a list")
                else:
                    for topic in summary.key_topics:
                        if not isinstance(topic, str):
                            errors.append("Key topic is not a string")
            
        except Exception as e:
            errors.append(f"Exception during summary validation: {str(e)}")
        
        return len(errors) == 0, errors
    
    def validate_user_preferences(self, preferences: UserPreferences) -> Tuple[bool, List[str]]:
        """
        Validate user preferences for data integrity.
        
        Args:
            preferences: The user preferences to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if not preferences.user_id:
                errors.append("User ID is missing")
            
            if not preferences.last_updated:
                errors.append("Last updated timestamp is missing")
            elif not isinstance(preferences.last_updated, datetime):
                errors.append("Last updated is not a datetime object")
            
            # Validate response style if present
            if hasattr(preferences, 'response_style') and preferences.response_style:
                if hasattr(preferences.response_style, 'tone') and preferences.response_style.tone:
                    valid_tones = ['formal', 'casual', 'friendly', 'professional', 'neutral']
                    if preferences.response_style.tone not in valid_tones:
                        errors.append(f"Invalid response style tone: {preferences.response_style.tone}")
            
        except Exception as e:
            errors.append(f"Exception during preferences validation: {str(e)}")
        
        return len(errors) == 0, errors
    
    def quarantine_corrupted_data(self, data: Any, corruption_reason: str, metadata: Dict[str, Any] = None) -> str:
        """
        Quarantine corrupted data for later analysis.
        
        Args:
            data: The corrupted data
            corruption_reason: Reason for quarantine
            metadata: Additional metadata about the corruption
            
        Returns:
            Quarantine ID for the stored data
        """
        try:
            # Generate unique quarantine ID
            data_id = f"quarantine_{datetime.now().timestamp()}_{len(self._quarantine_storage)}"
            
            quarantine_entry = {
                'data_id': data_id,
                'data': data,
                'corruption_reason': corruption_reason,
                'quarantine_timestamp': datetime.now(timezone.utc),
                'data_type': type(data).__name__,
                'metadata': metadata or {}
            }
            
            self._quarantine_storage[data_id] = quarantine_entry
            
            # Log the corruption
            corruption_log_entry = {
                'data_id': data_id,
                'corruption_reason': corruption_reason,
                'timestamp': datetime.now(timezone.utc),
                'data_type': type(data).__name__
            }
            self._corruption_log.append(corruption_log_entry)
            
            logger.warning(f"Data quarantined: {data_id} - {corruption_reason}")
            return data_id
            
        except Exception as e:
            logger.error(f"Error quarantining data: {e}")
            return ""
    
    def create_backup(self, data_id: str, data: Any) -> bool:
        """
        Create a backup of data before processing.
        
        Args:
            data_id: Unique identifier for the data
            data: The data to backup
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            backup_entry = {
                'data_id': data_id,
                'data': data,
                'backup_timestamp': datetime.now(timezone.utc),
                'checksum': self.calculate_checksum(data)
            }
            
            self._backup_storage[data_id] = backup_entry
            logger.debug(f"Created backup for data: {data_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup for {data_id}: {e}")
            return False
    
    def restore_from_backup(self, data_id: str) -> Optional[Any]:
        """
        Restore data from backup.
        
        Args:
            data_id: Unique identifier for the data
            
        Returns:
            Restored data if available, None otherwise
        """
        try:
            if data_id not in self._backup_storage:
                logger.warning(f"No backup found for data: {data_id}")
                return None
            
            backup_entry = self._backup_storage[data_id]
            data = backup_entry['data']
            
            # Verify backup integrity
            if not self.verify_checksum(data, backup_entry['checksum']):
                logger.error(f"Backup data integrity check failed for: {data_id}")
                return None
            
            logger.info(f"Restored data from backup: {data_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error restoring backup for {data_id}: {e}")
            return None
    
    def detect_corruption_patterns(self, data: Any) -> List[str]:
        """
        Detect common corruption patterns in data.
        
        Args:
            data: The data to analyze
            
        Returns:
            List of detected corruption patterns
        """
        patterns = []
        
        try:
            # Check patterns in the raw data structure first
            if isinstance(data, dict):
                # Check each value in the dictionary
                for key, value in data.items():
                    if isinstance(value, str):
                        # Check for null bytes
                        if '\x00' in value:
                            patterns.append('null_bytes')
                        
                        # Check for encoding issues (replacement characters)
                        if '\ufffd' in value:
                            patterns.append('encoding_issues')
                        
                        # Check for potential truncation (ends mid-word)
                        if len(value) > 10 and value.endswith(('trunca', 'corrup', 'incom')):
                            if 'truncation' not in patterns:
                                patterns.append('truncation')
            
            # Also check the string representation
            data_str = str(data)
            
            # Additional checks on string representation
            if '\x00' in data_str and 'null_bytes' not in patterns:
                patterns.append('null_bytes')
            
            if '\ufffd' in data_str and 'encoding_issues' not in patterns:
                patterns.append('encoding_issues')
            
        except Exception as e:
            logger.error(f"Error detecting corruption patterns: {e}")
        
        return patterns
    
    def attempt_recovery(self, corrupted_data: Any) -> Optional[Any]:
        """
        Attempt to recover corrupted data using simple cleanup strategies.
        
        Args:
            corrupted_data: The corrupted data
            
        Returns:
            Recovered data if possible, None otherwise
        """
        try:
            if not isinstance(corrupted_data, dict):
                return None
            
            recovered_data = corrupted_data.copy()
            
            # Clean null bytes from string fields recursively
            def clean_strings(obj):
                if isinstance(obj, dict):
                    return {k: clean_strings(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_strings(item) for item in obj]
                elif isinstance(obj, str):
                    # Remove null bytes and replacement characters
                    cleaned = obj.replace('\x00', '').replace('\ufffd', '')
                    return cleaned
                else:
                    return obj
            
            recovered_data = clean_strings(recovered_data)
            
            # Basic validation - if critical fields are None, can't recover
            if recovered_data.get('id') is None or recovered_data.get('content') is None:
                return None
            
            return recovered_data
            
        except Exception as e:
            logger.error(f"Error during data recovery: {e}")
            return None
    
    def attempt_data_recovery(self, corrupted_data: Any, data_type: str) -> Optional[Any]:
        """
        Attempt to recover corrupted data using various strategies.
        
        Args:
            corrupted_data: The corrupted data
            data_type: Type of data (conversation, message, etc.)
            
        Returns:
            Recovered data if possible, None otherwise
        """
        try:
            if data_type == 'conversation':
                return self._recover_conversation(corrupted_data)
            elif data_type == 'message':
                return self._recover_message(corrupted_data)
            elif data_type == 'conversation_summary':
                return self._recover_conversation_summary(corrupted_data)
            else:
                logger.warning(f"No recovery strategy for data type: {data_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error during data recovery: {e}")
            return None
    
    def _recover_conversation(self, corrupted_conversation: Any) -> Optional[Conversation]:
        """Attempt to recover a corrupted conversation."""
        try:
            # Try to extract what we can from the corrupted data
            recovered_data = {}
            
            # Extract basic fields
            if hasattr(corrupted_conversation, 'id') and corrupted_conversation.id:
                recovered_data['id'] = corrupted_conversation.id
            else:
                recovered_data['id'] = f"recovered_{datetime.now().timestamp()}"
            
            if hasattr(corrupted_conversation, 'user_id') and corrupted_conversation.user_id:
                recovered_data['user_id'] = corrupted_conversation.user_id
            else:
                logger.warning("Cannot recover conversation without user_id")
                return None
            
            if hasattr(corrupted_conversation, 'timestamp') and corrupted_conversation.timestamp:
                recovered_data['timestamp'] = corrupted_conversation.timestamp
            else:
                recovered_data['timestamp'] = datetime.now(timezone.utc)
            
            # Try to recover messages
            messages = []
            if hasattr(corrupted_conversation, 'messages') and corrupted_conversation.messages:
                for msg in corrupted_conversation.messages:
                    recovered_msg = self._recover_message(msg)
                    if recovered_msg:
                        messages.append(recovered_msg)
            
            recovered_data['messages'] = messages
            
            # Create recovered conversation
            recovered_conversation = Conversation(**recovered_data)
            
            logger.info(f"Recovered conversation {recovered_data['id']} with {len(messages)} messages")
            return recovered_conversation
            
        except Exception as e:
            logger.error(f"Failed to recover conversation: {e}")
            return None
    
    def _recover_message(self, corrupted_message: Any) -> Optional[Message]:
        """Attempt to recover a corrupted message."""
        try:
            recovered_data = {}
            
            # Extract basic fields
            if hasattr(corrupted_message, 'id') and corrupted_message.id:
                recovered_data['id'] = corrupted_message.id
            else:
                recovered_data['id'] = f"recovered_msg_{datetime.now().timestamp()}"
            
            if hasattr(corrupted_message, 'role') and corrupted_message.role:
                recovered_data['role'] = corrupted_message.role
            else:
                recovered_data['role'] = 'user'  # Default to user
            
            if hasattr(corrupted_message, 'content') and corrupted_message.content:
                recovered_data['content'] = str(corrupted_message.content)
            else:
                recovered_data['content'] = "[Content corrupted - unable to recover]"
            
            if hasattr(corrupted_message, 'timestamp') and corrupted_message.timestamp:
                recovered_data['timestamp'] = corrupted_message.timestamp
            else:
                recovered_data['timestamp'] = datetime.now(timezone.utc)
            
            recovered_message = Message(**recovered_data)
            
            logger.debug(f"Recovered message {recovered_data['id']}")
            return recovered_message
            
        except Exception as e:
            logger.error(f"Failed to recover message: {e}")
            return None
    
    def _recover_conversation_summary(self, corrupted_summary: Any) -> Optional[ConversationSummary]:
        """Attempt to recover a corrupted conversation summary."""
        try:
            recovered_data = {}
            
            if hasattr(corrupted_summary, 'conversation_id') and corrupted_summary.conversation_id:
                recovered_data['conversation_id'] = corrupted_summary.conversation_id
            else:
                logger.warning("Cannot recover summary without conversation_id")
                return None
            
            if hasattr(corrupted_summary, 'timestamp') and corrupted_summary.timestamp:
                recovered_data['timestamp'] = corrupted_summary.timestamp
            else:
                recovered_data['timestamp'] = datetime.now(timezone.utc)
            
            if hasattr(corrupted_summary, 'summary_text') and corrupted_summary.summary_text:
                recovered_data['summary_text'] = str(corrupted_summary.summary_text)
            else:
                recovered_data['summary_text'] = "[Summary corrupted - unable to recover]"
            
            # Optional fields with defaults
            recovered_data['message_count'] = getattr(corrupted_summary, 'message_count', 0)
            recovered_data['importance_score'] = getattr(corrupted_summary, 'importance_score', 0.5)
            recovered_data['key_topics'] = getattr(corrupted_summary, 'key_topics', [])
            
            recovered_summary = ConversationSummary(**recovered_data)
            
            logger.info(f"Recovered conversation summary {recovered_data['conversation_id']}")
            return recovered_summary
            
        except Exception as e:
            logger.error(f"Failed to recover conversation summary: {e}")
            return None
    
    def get_quarantine_stats(self) -> Dict[str, Any]:
        """Get statistics about quarantined data."""
        if not self._quarantine_storage:
            return {
                "total_quarantined": 0,
                "corruption_types": {},
                "oldest_quarantine": None,
                "newest_quarantine": None
            }
        
        corruption_types = {}
        timestamps = []
        
        for entry in self._quarantine_storage.values():
            corruption_reason = entry['corruption_reason']
            corruption_types[corruption_reason] = corruption_types.get(corruption_reason, 0) + 1
            timestamps.append(entry['quarantine_timestamp'])
        
        return {
            "total_quarantined": len(self._quarantine_storage),
            "corruption_types": corruption_types,
            "oldest_quarantine": min(timestamps).isoformat() if timestamps else None,
            "newest_quarantine": max(timestamps).isoformat() if timestamps else None
        }
    
    def clear_quarantine(self) -> int:
        """Clear all quarantined data and return count of cleared items."""
        count = len(self._quarantine_storage)
        self._quarantine_storage.clear()
        logger.info(f"Cleared {count} quarantined items")
        return count
    
    def get_corruption_report(self) -> Dict[str, Any]:
        """Get a report of all detected corruptions."""
        return {
            'total_corruptions': len(self._corruption_log),
            'quarantined_items': len(self._quarantine_storage),
            'backup_items': len(self._backup_storage),
            'recent_corruptions': self._corruption_log[-10:],  # Last 10 corruptions
            'corruption_by_type': self._get_corruption_stats_by_type()
        }
    
    def _get_corruption_stats_by_type(self) -> Dict[str, int]:
        """Get corruption statistics by data type."""
        stats = {}
        for entry in self._corruption_log:
            data_type = entry.get('data_type', 'unknown')
            stats[data_type] = stats.get(data_type, 0) + 1
        return stats
    
    def cleanup_quarantine(self, older_than_days: int = 30) -> int:
        """
        Clean up old quarantined data.
        
        Args:
            older_than_days: Remove quarantined data older than this many days
            
        Returns:
            Number of items removed
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            items_to_remove = []
            
            for data_id, entry in self._quarantine_storage.items():
                if entry['quarantine_timestamp'] < cutoff_date:
                    items_to_remove.append(data_id)
            
            for data_id in items_to_remove:
                del self._quarantine_storage[data_id]
            
            logger.info(f"Cleaned up {len(items_to_remove)} old quarantined items")
            return len(items_to_remove)
            
        except Exception as e:
            logger.error(f"Error cleaning up quarantine: {e}")
            return 0
    
    def cleanup_backups(self, older_than_days: int = 7) -> int:
        """
        Clean up old backup data.
        
        Args:
            older_than_days: Remove backup data older than this many days
            
        Returns:
            Number of items removed
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            items_to_remove = []
            
            for data_id, entry in self._backup_storage.items():
                if entry['backup_timestamp'] < cutoff_date:
                    items_to_remove.append(data_id)
            
            for data_id in items_to_remove:
                del self._backup_storage[data_id]
            
            logger.info(f"Cleaned up {len(items_to_remove)} old backup items")
            return len(items_to_remove)
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0
    
    def create_critical_data_backup(self, user_id: str, data: Dict[str, Any]) -> str:
        """
        Create a backup of critical user data (conversations, preferences, etc.).
        
        Args:
            user_id: User identifier
            data: Critical data to backup
            
        Returns:
            Backup ID for the stored data
        """
        try:
            backup_id = f"critical_{user_id}_{datetime.now().timestamp()}"
            
            backup_entry = {
                'backup_id': backup_id,
                'user_id': user_id,
                'data': data,
                'backup_timestamp': datetime.now(timezone.utc),
                'checksum': self.calculate_checksum(data),
                'backup_type': 'critical'
            }
            
            self._backup_storage[backup_id] = backup_entry
            logger.info(f"Created critical data backup: {backup_id} for user {user_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Error creating critical data backup for user {user_id}: {e}")
            return ""
    
    def restore_critical_data_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore critical data from backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Restored critical data if available, None otherwise
        """
        try:
            if backup_id not in self._backup_storage:
                logger.warning(f"No critical backup found: {backup_id}")
                return None
            
            backup_entry = self._backup_storage[backup_id]
            
            # Verify this is a critical backup
            if backup_entry.get('backup_type') != 'critical':
                logger.error(f"Backup {backup_id} is not a critical data backup")
                return None
            
            data = backup_entry['data']
            
            # Verify backup integrity
            if not self.verify_checksum(data, backup_entry['checksum']):
                logger.error(f"Critical backup integrity check failed: {backup_id}")
                return None
            
            logger.info(f"Restored critical data from backup: {backup_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error restoring critical backup {backup_id}: {e}")
            return None
    
    def list_critical_backups(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available critical data backups.
        
        Args:
            user_id: Optional user ID to filter backups
            
        Returns:
            List of backup information
        """
        try:
            backups = []
            
            for backup_id, entry in self._backup_storage.items():
                if entry.get('backup_type') == 'critical':
                    if user_id is None or entry.get('user_id') == user_id:
                        backup_info = {
                            'backup_id': backup_id,
                            'user_id': entry.get('user_id'),
                            'timestamp': entry['backup_timestamp'].isoformat(),
                            'checksum': entry['checksum'][:8] + '...'  # Truncated for display
                        }
                        backups.append(backup_info)
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing critical backups: {e}")
            return []
    
    def validate_backup_integrity(self, backup_id: str) -> Tuple[bool, List[str]]:
        """
        Validate the integrity of a backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if backup_id not in self._backup_storage:
                errors.append(f"Backup {backup_id} not found")
                return False, errors
            
            backup_entry = self._backup_storage[backup_id]
            
            # Check required fields
            required_fields = ['data', 'backup_timestamp', 'checksum']
            for field in required_fields:
                if field not in backup_entry:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return False, errors
            
            # Verify checksum
            data = backup_entry['data']
            expected_checksum = backup_entry['checksum']
            
            if not self.verify_checksum(data, expected_checksum):
                errors.append("Checksum verification failed")
            
            # Check timestamp validity
            timestamp = backup_entry['backup_timestamp']
            if not isinstance(timestamp, datetime):
                errors.append("Invalid timestamp format")
            elif timestamp > datetime.now(timezone.utc):
                errors.append("Backup timestamp is in the future")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Exception during backup validation: {str(e)}")
            return False, errors