"""
Storage layer with integrated data integrity checking and corruption handling.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from ..interfaces import StorageLayerInterface
from ..models import (
    Conversation, ConversationSummary, UserPreferences, 
    PrivacySettings, SearchResult
)
from ..utils.storage_backends import HybridStorageBackend
from .data_integrity_service import DataIntegrityService, DataCorruptionError
from .storage_layer import StorageLayer

logger = logging.getLogger(__name__)


class IntegrityAwareStorageLayer(StorageLayerInterface):
    """
    Storage layer with integrated data integrity checking, corruption detection,
    and automatic recovery mechanisms.
    """
    
    def __init__(self, base_storage: Optional[StorageLayer] = None):
        """Initialize the integrity-aware storage layer."""
        self._base_storage = base_storage or StorageLayer()
        self.integrity_service = DataIntegrityService()
        self._integrity_service = self.integrity_service  # For backward compatibility
        self._initialized = False
        self._corruption_tolerance_enabled = False  # Default to strict mode for tests
        self._auto_recovery_enabled = True
        
    async def initialize(self) -> None:
        """Initialize the storage layer with integrity checking."""
        if not self._initialized:
            await self._base_storage.initialize()
            self._initialized = True
            logger.info("IntegrityAwareStorageLayer initialized")
    
    async def close(self) -> None:
        """Close the storage layer."""
        if self._initialized:
            await self._base_storage.close()
            self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure the storage layer is initialized."""
        if not self._initialized:
            await self.initialize()
    
    def enable_corruption_tolerance(self, enabled: bool = True) -> None:
        """Enable or disable corruption tolerance mode."""
        self._corruption_tolerance_enabled = enabled
        logger.info(f"Corruption tolerance {'enabled' if enabled else 'disabled'}")
    
    def enable_auto_recovery(self, enabled: bool = True) -> None:
        """Enable or disable automatic data recovery."""
        self._auto_recovery_enabled = enabled
        logger.info(f"Auto recovery {'enabled' if enabled else 'disabled'}")
    
    # Conversation storage with integrity checking
    async def store_conversation(self, user_id: str, conversation: Conversation) -> None:
        """Store a conversation with integrity validation."""
        await self._ensure_initialized()
        
        try:
            # Validate conversation before storing
            is_valid, errors = self._integrity_service.validate_conversation(conversation)
            
            if not is_valid:
                error_msg = f"Conversation validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                
                if not self._corruption_tolerance_enabled:
                    raise DataCorruptionError(error_msg)
                
                # Attempt to recover the conversation
                if self._auto_recovery_enabled:
                    recovered_conversation = self._integrity_service.attempt_data_recovery(
                        conversation, 'conversation'
                    )
                    if recovered_conversation:
                        conversation = recovered_conversation
                        logger.info(f"Recovered conversation {conversation.id} before storing")
                    else:
                        logger.warning(f"Could not recover conversation {conversation.id}, storing as-is")
            
            # Create backup before storing
            backup_id = f"conv_{conversation.id}_{datetime.now().timestamp()}"
            self._integrity_service.create_backup(backup_id, conversation)
            
            # Calculate and add integrity metadata
            checksum = self._integrity_service.calculate_checksum(conversation)
            conversation.metadata.additional_data['integrity'] = {
                'checksum': checksum,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            
            # Store the conversation
            await self._base_storage.store_conversation(user_id, conversation)
            
            logger.debug(f"Stored conversation {conversation.id} with checksum {checksum[:8]}...")
            
        except Exception as e:
            logger.error(f"Error storing conversation {conversation.id}: {e}")
            
            # Quarantine the corrupted data
            self._integrity_service.quarantine_corrupted_data(
                f"conv_{conversation.id}",
                conversation,
                f"Storage error: {str(e)}"
            )
            
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation with integrity verification."""
        await self._ensure_initialized()
        
        try:
            conversation = await self._base_storage.get_conversation(conversation_id)
            
            if conversation is None:
                return None
            
            # Check integrity metadata if present
            integrity_data = conversation.metadata.additional_data.get('integrity')
            if integrity_data and 'checksum' in integrity_data:
                # Verify checksum
                expected_checksum = integrity_data['checksum']
                # Create a copy without integrity metadata for checksum calculation
                temp_conversation = conversation.model_copy(deep=True)
                temp_conversation.metadata.additional_data.pop('integrity', None)
                
                if not self._integrity_service.verify_checksum(temp_conversation, expected_checksum):
                    logger.warning(f"Checksum verification failed for conversation {conversation_id}")
                    if not self._corruption_tolerance_enabled:
                        raise DataCorruptionError("Checksum verification failed")
            
            # Validate retrieved conversation
            is_valid, errors = self._integrity_service.validate_conversation(conversation)
            
            if not is_valid:
                logger.warning(f"Retrieved corrupted conversation {conversation_id}: {'; '.join(errors)}")
                
                if not self._corruption_tolerance_enabled:
                    raise DataCorruptionError(f"Corrupted conversation: {'; '.join(errors)}")
                
                # Attempt recovery
                if self._auto_recovery_enabled:
                    recovered_conversation = self._integrity_service.attempt_data_recovery(
                        conversation, 'conversation'
                    )
                    if recovered_conversation:
                        logger.info(f"Recovered conversation {conversation_id} during retrieval")
                        return recovered_conversation
                
                # Quarantine corrupted data
                self._integrity_service.quarantine_corrupted_data(
                    f"conv_{conversation_id}",
                    conversation,
                    f"Retrieval validation failed: {'; '.join(errors)}"
                )
                
                # Try to restore from backup
                backup_id = f"conv_{conversation_id}"
                restored_conversation = self._integrity_service.restore_from_backup(backup_id)
                if restored_conversation:
                    logger.info(f"Restored conversation {conversation_id} from backup")
                    return restored_conversation
                
                if not self._corruption_tolerance_enabled:
                    return None
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {e}")
            
            # Try to restore from backup on any error
            backup_id = f"conv_{conversation_id}"
            restored_conversation = self._integrity_service.restore_from_backup(backup_id)
            if restored_conversation:
                logger.info(f"Restored conversation {conversation_id} from backup after error")
                return restored_conversation
            
            raise
    
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get conversations for a user with integrity checking."""
        await self._ensure_initialized()
        
        try:
            conversations = await self._base_storage.get_user_conversations(
                user_id, limit, start_date, end_date
            )
            
            # Validate each conversation
            valid_conversations = []
            corrupted_count = 0
            
            for conversation in conversations:
                is_valid, errors = self._integrity_service.validate_conversation(conversation)
                
                if is_valid:
                    valid_conversations.append(conversation)
                else:
                    corrupted_count += 1
                    logger.warning(f"Corrupted conversation {conversation.id}: {'; '.join(errors)}")
                    
                    if self._auto_recovery_enabled:
                        recovered_conversation = self._integrity_service.attempt_data_recovery(
                            conversation, 'conversation'
                        )
                        if recovered_conversation:
                            valid_conversations.append(recovered_conversation)
                            logger.info(f"Recovered conversation {conversation.id}")
                        else:
                            # Quarantine corrupted data
                            self._integrity_service.quarantine_corrupted_data(
                                f"conv_{conversation.id}",
                                conversation,
                                f"Validation failed: {'; '.join(errors)}"
                            )
                    
                    elif self._corruption_tolerance_enabled:
                        # Include corrupted data with warning
                        valid_conversations.append(conversation)
            
            if corrupted_count > 0:
                logger.warning(f"Found {corrupted_count} corrupted conversations for user {user_id}")
            
            return valid_conversations
            
        except Exception as e:
            logger.error(f"Error retrieving conversations for user {user_id}: {e}")
            raise
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation with backup creation."""
        await self._ensure_initialized()
        
        try:
            # Create backup before deletion
            conversation = await self.get_conversation(conversation_id)
            if conversation:
                backup_id = f"deleted_conv_{conversation_id}_{datetime.now().timestamp()}"
                self._integrity_service.create_backup(backup_id, conversation)
                logger.info(f"Created backup before deleting conversation {conversation_id}")
            
            await self._base_storage.delete_conversation(conversation_id)
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            raise
    
    # Conversation summary storage with integrity checking
    async def store_conversation_summary(self, user_id: str, summary: ConversationSummary) -> None:
        """Store a conversation summary with validation."""
        await self._ensure_initialized()
        
        try:
            # Validate summary before storing
            is_valid, errors = self._integrity_service.validate_conversation_summary(summary)
            
            if not is_valid:
                error_msg = f"Summary validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                
                if not self._corruption_tolerance_enabled:
                    raise DataCorruptionError(error_msg)
                
                # Attempt recovery
                if self._auto_recovery_enabled:
                    recovered_summary = self._integrity_service.attempt_data_recovery(
                        summary, 'conversation_summary'
                    )
                    if recovered_summary:
                        summary = recovered_summary
                        logger.info(f"Recovered summary for conversation {summary.conversation_id}")
            
            # Create backup
            backup_id = f"summary_{summary.conversation_id}_{datetime.now().timestamp()}"
            self._integrity_service.create_backup(backup_id, summary)
            
            await self._base_storage.store_conversation_summary(user_id, summary)
            
        except Exception as e:
            logger.error(f"Error storing summary for conversation {summary.conversation_id}: {e}")
            
            # Quarantine corrupted data
            self._integrity_service.quarantine_corrupted_data(
                f"summary_{summary.conversation_id}",
                summary,
                f"Storage error: {str(e)}"
            )
            
            raise
    
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries with integrity checking."""
        await self._ensure_initialized()
        
        try:
            summaries = await self._base_storage.get_conversation_summaries(user_id, limit)
            
            # Validate each summary
            valid_summaries = []
            corrupted_count = 0
            
            for summary in summaries:
                is_valid, errors = self._integrity_service.validate_conversation_summary(summary)
                
                if is_valid:
                    valid_summaries.append(summary)
                else:
                    corrupted_count += 1
                    logger.warning(f"Corrupted summary {summary.conversation_id}: {'; '.join(errors)}")
                    
                    if self._auto_recovery_enabled:
                        recovered_summary = self._integrity_service.attempt_data_recovery(
                            summary, 'conversation_summary'
                        )
                        if recovered_summary:
                            valid_summaries.append(recovered_summary)
                            logger.info(f"Recovered summary {summary.conversation_id}")
                        else:
                            # Quarantine corrupted data
                            self._integrity_service.quarantine_corrupted_data(
                                f"summary_{summary.conversation_id}",
                                summary,
                                f"Validation failed: {'; '.join(errors)}"
                            )
                    
                    elif self._corruption_tolerance_enabled:
                        valid_summaries.append(summary)
            
            if corrupted_count > 0:
                logger.warning(f"Found {corrupted_count} corrupted summaries for user {user_id}")
            
            return valid_summaries
            
        except Exception as e:
            logger.error(f"Error retrieving summaries for user {user_id}: {e}")
            raise
    
    # User preferences storage with integrity checking
    async def store_user_preferences(self, user_id: str, preferences: UserPreferences) -> None:
        """Store user preferences with validation."""
        await self._ensure_initialized()
        
        try:
            # Validate preferences
            is_valid, errors = self._integrity_service.validate_user_preferences(preferences)
            
            if not is_valid:
                error_msg = f"Preferences validation failed: {'; '.join(errors)}"
                logger.error(error_msg)
                
                if not self._corruption_tolerance_enabled:
                    raise DataCorruptionError(error_msg)
            
            # Create backup
            backup_id = f"prefs_{preferences.user_id}_{datetime.now().timestamp()}"
            self._integrity_service.create_backup(backup_id, preferences)
            
            await self._base_storage.store_user_preferences(user_id, preferences)
            
        except Exception as e:
            logger.error(f"Error storing preferences for user {preferences.user_id}: {e}")
            
            # Quarantine corrupted data
            self._integrity_service.quarantine_corrupted_data(
                f"prefs_{preferences.user_id}",
                preferences,
                f"Storage error: {str(e)}"
            )
            
            raise
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences with integrity checking."""
        await self._ensure_initialized()
        
        try:
            preferences = await self._base_storage.get_user_preferences(user_id)
            
            if preferences is None:
                return None
            
            # Validate preferences
            is_valid, errors = self._integrity_service.validate_user_preferences(preferences)
            
            if not is_valid:
                logger.warning(f"Corrupted preferences for user {user_id}: {'; '.join(errors)}")
                
                if not self._corruption_tolerance_enabled:
                    raise DataCorruptionError(f"Corrupted preferences: {'; '.join(errors)}")
                
                # Try to restore from backup
                backup_id = f"prefs_{user_id}"
                restored_preferences = self._integrity_service.restore_from_backup(backup_id)
                if restored_preferences:
                    logger.info(f"Restored preferences for user {user_id} from backup")
                    return restored_preferences
                
                # Quarantine corrupted data
                self._integrity_service.quarantine_corrupted_data(
                    f"prefs_{user_id}",
                    preferences,
                    f"Validation failed: {'; '.join(errors)}"
                )
                
                if not self._corruption_tolerance_enabled:
                    return None
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error retrieving preferences for user {user_id}: {e}")
            
            # Try to restore from backup
            backup_id = f"prefs_{user_id}"
            restored_preferences = self._integrity_service.restore_from_backup(backup_id)
            if restored_preferences:
                logger.info(f"Restored preferences for user {user_id} from backup after error")
                return restored_preferences
            
            raise
    
    # Privacy settings storage (delegated to base storage for now)
    async def store_privacy_settings(self, user_id: str, settings: PrivacySettings) -> None:
        """Store privacy settings."""
        await self._ensure_initialized()
        return await self._base_storage.store_privacy_settings(user_id, settings)
    
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings."""
        await self._ensure_initialized()
        return await self._base_storage.get_privacy_settings(user_id)
    
    # Data management methods
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all data for a user with backup creation."""
        await self._ensure_initialized()
        
        try:
            # Create backup before deletion
            user_data = await self.get_user_data_summary(user_id)
            backup_id = f"deleted_user_{user_id}_{datetime.now().timestamp()}"
            self._integrity_service.create_backup(backup_id, user_data)
            logger.info(f"Created backup before deleting all data for user {user_id}")
            
            await self._base_storage.delete_all_user_data(user_id)
            
        except Exception as e:
            logger.error(f"Error deleting all data for user {user_id}: {e}")
            raise
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of all user data."""
        await self._ensure_initialized()
        return await self._base_storage.get_user_data_summary(user_id)
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data according to retention policies."""
        await self._ensure_initialized()
        await self._base_storage.cleanup_expired_data()
    
    # Health check and maintenance
    async def health_check(self) -> bool:
        """Perform health check including integrity status."""
        await self._ensure_initialized()
        
        try:
            base_health = await self._base_storage.health_check()
            return base_health and self._initialized
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_detailed_health_status(self) -> Dict[str, Any]:
        """Get detailed health status including integrity information."""
        await self._ensure_initialized()
        
        base_health = await self._base_storage.health_check()
        corruption_report = self._integrity_service.get_corruption_report()
        
        return {
            "base_storage": base_health,
            "integrity_service": {
                "corruption_tolerance_enabled": self._corruption_tolerance_enabled,
                "auto_recovery_enabled": self._auto_recovery_enabled,
                "corruption_report": corruption_report
            }
        }
    
    async def cleanup_integrity_data(self, backup_days: int = 7, quarantine_days: int = 30) -> Dict[str, int]:
        """Clean up old integrity data."""
        try:
            backup_cleaned = self._integrity_service.cleanup_backups(backup_days)
            quarantine_cleaned = self._integrity_service.cleanup_quarantine(quarantine_days)
            
            logger.info(f"Cleaned up {backup_cleaned} backups and {quarantine_cleaned} quarantined items")
            
            return {
                "backups_cleaned": backup_cleaned,
                "quarantine_cleaned": quarantine_cleaned
            }
            
        except Exception as e:
            logger.error(f"Error during integrity data cleanup: {e}")
            return {"error": str(e)}
    
    def get_integrity_service(self) -> DataIntegrityService:
        """Get the underlying integrity service for advanced operations."""
        return self._integrity_service