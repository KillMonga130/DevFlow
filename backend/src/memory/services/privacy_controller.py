"""
Privacy controller service implementation.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from ..interfaces import PrivacyControllerInterface
from ..models import (
    PrivacySettings, DeleteOptions, UserDataExport, DeleteScope,
    DataRetentionPolicy, PrivacyMode
)
from ..services.storage_layer import StorageLayer
from ..config import get_memory_config

logger = logging.getLogger(__name__)


class PrivacyController(PrivacyControllerInterface):
    """Privacy controller service implementation."""
    
    def __init__(self, storage_layer: Optional[StorageLayer] = None):
        """Initialize the privacy controller."""
        self._storage = storage_layer or StorageLayer()
        self._config = get_memory_config()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the privacy controller."""
        if not self._initialized:
            await self._storage.initialize()
            self._initialized = True
    
    async def delete_user_data(self, user_id: str, options: DeleteOptions) -> None:
        """Delete user data according to the specified options."""
        await self._ensure_initialized()
        
        if not options.confirm_deletion:
            raise ValueError("Deletion must be explicitly confirmed")
        
        await self.audit_data_access(
            user_id, 
            "DELETE_REQUEST", 
            f"Scope: {options.scope}, Reason: {options.reason or 'Not specified'}"
        )
        
        try:
            if options.scope == DeleteScope.ALL_DATA:
                await self._delete_all_user_data(user_id)
            elif options.scope == DeleteScope.CONVERSATIONS:
                await self._delete_user_conversations(user_id, options)
            elif options.scope == DeleteScope.PREFERENCES:
                await self._delete_user_preferences(user_id)
            elif options.scope == DeleteScope.SEARCH_HISTORY:
                await self._delete_search_history(user_id)
            elif options.scope == DeleteScope.SPECIFIC_CONVERSATIONS:
                if not options.conversation_ids:
                    raise ValueError("Conversation IDs required for specific conversation deletion")
                await self._delete_specific_conversations(user_id, options.conversation_ids)
            elif options.scope == DeleteScope.DATE_RANGE:
                if not options.date_range_start and not options.date_range_end:
                    raise ValueError("Date range required for date range deletion")
                await self._delete_conversations_by_date_range(user_id, options)
            
            await self.audit_data_access(
                user_id, 
                "DELETE_COMPLETED", 
                f"Successfully deleted data with scope: {options.scope}"
            )
            
        except Exception as e:
            await self.audit_data_access(
                user_id, 
                "DELETE_FAILED", 
                f"Failed to delete data: {str(e)}"
            )
            raise
    
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data for download."""
        await self._ensure_initialized()
        
        await self.audit_data_access(user_id, "EXPORT_REQUEST", "Full data export requested")
        
        try:
            # Get all user conversations
            conversations = await self._storage.get_user_conversations(user_id)
            conversation_data = [conv.model_dump() for conv in conversations]
            
            # Get user preferences
            preferences = await self._storage.get_user_preferences(user_id)
            preferences_data = preferences.model_dump() if preferences else None
            
            # Get privacy settings
            privacy_settings = await self._storage.get_privacy_settings(user_id)
            privacy_data = privacy_settings.model_dump() if privacy_settings else None
            
            # Get search history (placeholder - would need search service integration)
            search_history = await self._get_search_history(user_id)
            
            # Create export
            export = UserDataExport(
                user_id=user_id,
                conversations=conversation_data,
                preferences=preferences_data,
                privacy_settings=privacy_data,
                search_history=search_history,
                metadata={
                    "export_version": "1.0",
                    "total_conversations": len(conversation_data),
                    "export_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            await self.audit_data_access(
                user_id, 
                "EXPORT_COMPLETED", 
                f"Exported {len(conversation_data)} conversations and associated data"
            )
            
            return export
            
        except Exception as e:
            await self.audit_data_access(
                user_id, 
                "EXPORT_FAILED", 
                f"Failed to export data: {str(e)}"
            )
            raise
    
    async def apply_retention_policy(self, user_id: str, settings: PrivacySettings) -> None:
        """Apply data retention policy for a user."""
        await self._ensure_initialized()
        
        await self.audit_data_access(
            user_id, 
            "RETENTION_POLICY_APPLIED", 
            f"Policy: {settings.data_retention_policy}"
        )
        
        if settings.data_retention_policy == DataRetentionPolicy.SESSION_ONLY:
            # Delete all stored data for session-only users
            await self._delete_all_user_data(user_id)
        elif settings.data_retention_policy != DataRetentionPolicy.INDEFINITE:
            # Calculate retention period
            retention_days = self._get_retention_days(settings.data_retention_policy)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Delete conversations older than retention period
            conversations = await self._storage.get_user_conversations(
                user_id, 
                end_date=cutoff_date
            )
            
            for conv in conversations:
                await self._storage.delete_conversation(conv.id)
            
            logger.info(f"Applied retention policy for user {user_id}: deleted {len(conversations)} old conversations")
    
    async def anonymize_data(self, user_id: str, conversation_ids: List[str]) -> None:
        """Anonymize specified conversations."""
        await self._ensure_initialized()
        
        await self.audit_data_access(
            user_id, 
            "ANONYMIZATION_REQUEST", 
            f"Anonymizing {len(conversation_ids)} conversations"
        )
        
        anonymized_count = 0
        for conv_id in conversation_ids:
            conversation = await self._storage.get_conversation(conv_id)
            if conversation and conversation.user_id == user_id:
                # Anonymize conversation by replacing sensitive content
                anonymized_conv = self._anonymize_conversation(conversation)
                await self._storage.store_conversation(anonymized_conv)
                anonymized_count += 1
        
        await self.audit_data_access(
            user_id, 
            "ANONYMIZATION_COMPLETED", 
            f"Anonymized {anonymized_count} conversations"
        )
    
    async def audit_data_access(self, user_id: str, operation: str, details: str) -> None:
        """Log data access for audit purposes."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "operation": operation,
            "details": details,
            "source": "privacy_controller"
        }
        
        # Log to application logger
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
        
        # TODO: In production, this should also write to a dedicated audit log store
        # that is separate from application logs and has additional security measures
    
    async def check_privacy_compliance(self, user_id: str) -> bool:
        """Check if user data handling is compliant with privacy settings."""
        await self._ensure_initialized()
        
        try:
            # Get user's privacy settings
            settings = await self._storage.get_privacy_settings(user_id)
            if not settings:
                # Default settings are compliant
                return True
            
            # Check if data retention is being followed
            if settings.data_retention_policy != DataRetentionPolicy.INDEFINITE:
                retention_days = self._get_retention_days(settings.data_retention_policy)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
                
                # Check if there are conversations older than retention period
                old_conversations = await self._storage.get_user_conversations(
                    user_id, 
                    end_date=cutoff_date,
                    limit=1
                )
                
                if old_conversations:
                    logger.warning(f"Privacy compliance issue: User {user_id} has data older than retention policy")
                    return False
            
            # Check if privacy mode is being respected
            if settings.privacy_mode == PrivacyMode.NO_MEMORY:
                # Should have no stored conversations
                conversations = await self._storage.get_user_conversations(user_id, limit=1)
                if conversations:
                    logger.warning(f"Privacy compliance issue: User {user_id} in NO_MEMORY mode has stored conversations")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check privacy compliance for user {user_id}: {e}")
            return False
    
    async def _delete_all_user_data(self, user_id: str) -> None:
        """Delete all data for a user."""
        await self._storage.delete_all_user_data(user_id)
        logger.info(f"Deleted all data for user {user_id}")
    
    async def _delete_user_conversations(self, user_id: str, options: DeleteOptions) -> None:
        """Delete user conversations based on options."""
        if options.date_range_start or options.date_range_end:
            await self._delete_conversations_by_date_range(user_id, options)
        else:
            # Delete all conversations
            conversations = await self._storage.get_user_conversations(user_id)
            for conv in conversations:
                await self._storage.delete_conversation(conv.id)
            logger.info(f"Deleted {len(conversations)} conversations for user {user_id}")
    
    async def _delete_user_preferences(self, user_id: str) -> None:
        """Delete user preferences."""
        # This would require a method in storage layer to delete preferences
        # For now, we'll store empty preferences
        from ..models.preferences import UserPreferences
        empty_prefs = UserPreferences(user_id=user_id)
        await self._storage.store_user_preferences(empty_prefs)
        logger.info(f"Cleared preferences for user {user_id}")
    
    async def _delete_search_history(self, user_id: str) -> None:
        """Delete search history for a user."""
        # This would integrate with search service to clear search history
        # Placeholder implementation
        logger.info(f"Cleared search history for user {user_id}")
    
    async def _delete_specific_conversations(self, user_id: str, conversation_ids: List[str]) -> None:
        """Delete specific conversations."""
        deleted_count = 0
        for conv_id in conversation_ids:
            conversation = await self._storage.get_conversation(conv_id)
            if conversation and conversation.user_id == user_id:
                await self._storage.delete_conversation(conv_id)
                deleted_count += 1
        logger.info(f"Deleted {deleted_count} specific conversations for user {user_id}")
    
    async def _delete_conversations_by_date_range(self, user_id: str, options: DeleteOptions) -> None:
        """Delete conversations within a date range."""
        conversations = await self._storage.get_user_conversations(
            user_id,
            start_date=options.date_range_start,
            end_date=options.date_range_end
        )
        
        for conv in conversations:
            await self._storage.delete_conversation(conv.id)
        
        logger.info(f"Deleted {len(conversations)} conversations in date range for user {user_id}")
    
    async def _get_search_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get search history for a user."""
        # This would integrate with search service
        # Placeholder implementation
        return []
    
    def _anonymize_conversation(self, conversation):
        """Anonymize a conversation by replacing sensitive content."""
        from ..models.conversation import Conversation, Message
        
        # Create anonymized messages
        anonymized_messages = []
        for msg in conversation.messages:
            anonymized_content = self._anonymize_text(msg.content)
            anonymized_msg = Message(
                id=msg.id,
                role=msg.role,
                content=anonymized_content,
                timestamp=msg.timestamp,
                metadata=msg.metadata
            )
            anonymized_messages.append(anonymized_msg)
        
        # Create anonymized conversation
        anonymized_conv = Conversation(
            id=conversation.id,
            user_id=conversation.user_id,
            timestamp=conversation.timestamp,
            messages=anonymized_messages,
            summary=self._anonymize_text(conversation.summary) if conversation.summary else None,
            tags=conversation.tags,
            metadata=conversation.metadata
        )
        
        return anonymized_conv
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize text by replacing sensitive information."""
        if not text:
            return text
        
        # Simple anonymization - replace with placeholder
        # In production, this would use more sophisticated techniques
        import re
        
        # Replace email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Replace phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Replace potential names (capitalized words)
        text = re.sub(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NAME]', text)
        
        return text
    
    def _get_retention_days(self, policy: DataRetentionPolicy) -> int:
        """Get the number of days for a retention policy."""
        policy_days = {
            DataRetentionPolicy.DAYS_30: 30,
            DataRetentionPolicy.DAYS_90: 90,
            DataRetentionPolicy.DAYS_365: 365,
        }
        return policy_days.get(policy, 90)  # Default to 90 days
    
    async def _ensure_initialized(self) -> None:
        """Ensure the privacy controller is initialized."""
        if not self._initialized:
            await self.initialize()