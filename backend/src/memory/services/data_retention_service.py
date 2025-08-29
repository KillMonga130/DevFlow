"""
Data retention and cleanup service for managing data lifecycle.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from ..models import (
    PrivacySettings, DataRetentionPolicy, Conversation, 
    UserPreferences, DeleteOptions, DeleteScope
)
from ..services.storage_layer import StorageLayer
from ..services.privacy_controller import PrivacyController
from ..config import get_memory_config

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for managing data retention policies and cleanup operations."""
    
    def __init__(
        self, 
        storage_layer: Optional[StorageLayer] = None,
        privacy_controller: Optional[PrivacyController] = None
    ):
        """Initialize the data retention service."""
        self._storage = storage_layer or StorageLayer()
        self._privacy_controller = privacy_controller or PrivacyController(self._storage)
        self._config = get_memory_config()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the data retention service."""
        if not self._initialized:
            await self._storage.initialize()
            await self._privacy_controller.initialize()
            self._initialized = True
    
    async def enforce_retention_policies(self, user_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enforce retention policies for specified users or all users."""
        await self._ensure_initialized()
        
        results = {
            "processed_users": 0,
            "deleted_conversations": 0,
            "archived_conversations": 0,
            "errors": [],
            "processing_time": 0
        }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get users to process
            if user_ids is None:
                user_ids = await self._get_all_user_ids()
            
            for user_id in user_ids:
                try:
                    user_results = await self._enforce_user_retention_policy(user_id)
                    results["deleted_conversations"] += user_results["deleted_conversations"]
                    results["archived_conversations"] += user_results["archived_conversations"]
                    results["processed_users"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process retention for user {user_id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            end_time = datetime.now(timezone.utc)
            results["processing_time"] = (end_time - start_time).total_seconds()
            
            await self._audit_retention_enforcement(results)
            
        except Exception as e:
            logger.error(f"Failed to enforce retention policies: {e}")
            results["errors"].append(f"Global error: {str(e)}")
        
        return results
    
    async def cleanup_expired_data(self) -> Dict[str, Any]:
        """Clean up expired data across all users."""
        await self._ensure_initialized()
        
        results = {
            "total_conversations_deleted": 0,
            "total_users_processed": 0,
            "storage_freed_mb": 0,
            "errors": []
        }
        
        try:
            # Get all users with privacy settings
            user_ids = await self._get_all_user_ids()
            
            for user_id in user_ids:
                try:
                    user_results = await self._cleanup_user_expired_data(user_id)
                    results["total_conversations_deleted"] += user_results["conversations_deleted"]
                    results["storage_freed_mb"] += user_results["storage_freed_mb"]
                    results["total_users_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to cleanup data for user {user_id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            await self._audit_cleanup_operation(results)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            results["errors"].append(f"Global cleanup error: {str(e)}")
        
        return results
    
    async def archive_old_conversations(
        self, 
        user_id: str, 
        archive_threshold_days: int = 365
    ) -> Dict[str, Any]:
        """Archive old conversations for a user."""
        await self._ensure_initialized()
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=archive_threshold_days)
        
        # Get old conversations
        old_conversations = await self._storage.get_user_conversations(
            user_id, 
            end_date=cutoff_date
        )
        
        archived_count = 0
        archived_size_mb = 0
        
        for conversation in old_conversations:
            try:
                # Calculate conversation size
                conv_size = self._calculate_conversation_size(conversation)
                
                # Archive conversation (compress and move to archive storage)
                await self._archive_conversation(conversation)
                
                archived_count += 1
                archived_size_mb += conv_size
                
            except Exception as e:
                logger.error(f"Failed to archive conversation {conversation.id}: {e}")
        
        results = {
            "user_id": user_id,
            "archived_conversations": archived_count,
            "archived_size_mb": archived_size_mb,
            "cutoff_date": cutoff_date.isoformat()
        }
        
        await self._audit_archival_operation(user_id, results)
        
        return results
    
    async def optimize_storage(self, user_id: str) -> Dict[str, Any]:
        """Optimize storage for a user by compressing and deduplicating data."""
        await self._ensure_initialized()
        
        results = {
            "user_id": user_id,
            "original_size_mb": 0,
            "optimized_size_mb": 0,
            "compression_ratio": 0,
            "deduplicated_messages": 0
        }
        
        try:
            # Get all user conversations
            conversations = await self._storage.get_user_conversations(user_id)
            
            original_size = sum(self._calculate_conversation_size(conv) for conv in conversations)
            results["original_size_mb"] = original_size
            
            # Optimize conversations
            optimized_conversations = []
            deduplicated_count = 0
            
            for conversation in conversations:
                optimized_conv, dedup_count = await self._optimize_conversation(conversation)
                optimized_conversations.append(optimized_conv)
                deduplicated_count += dedup_count
            
            # Calculate optimized size
            optimized_size = sum(self._calculate_conversation_size(conv) for conv in optimized_conversations)
            results["optimized_size_mb"] = optimized_size
            results["compression_ratio"] = (original_size - optimized_size) / original_size if original_size > 0 else 0
            results["deduplicated_messages"] = deduplicated_count
            
            # Store optimized conversations
            for conversation in optimized_conversations:
                await self._storage.store_conversation(conversation)
            
            await self._audit_optimization_operation(user_id, results)
            
        except Exception as e:
            logger.error(f"Failed to optimize storage for user {user_id}: {e}")
            raise
        
        return results
    
    async def get_retention_status(self, user_id: str) -> Dict[str, Any]:
        """Get retention status and statistics for a user."""
        await self._ensure_initialized()
        
        # Get user's privacy settings
        privacy_settings = await self._storage.get_privacy_settings(user_id)
        if not privacy_settings:
            privacy_settings = PrivacySettings(user_id=user_id)  # Default settings
        
        # Get conversation statistics
        conversations = await self._storage.get_user_conversations(user_id)
        
        # Calculate retention metrics
        now = datetime.now(timezone.utc)
        retention_days = self._get_retention_days(privacy_settings.data_retention_policy)
        
        if retention_days > 0:
            cutoff_date = now - timedelta(days=retention_days)
            expired_conversations = [
                conv for conv in conversations 
                if conv.timestamp < cutoff_date
            ]
        else:
            expired_conversations = []
        
        # Calculate storage usage
        total_storage_mb = sum(self._calculate_conversation_size(conv) for conv in conversations)
        expired_storage_mb = sum(self._calculate_conversation_size(conv) for conv in expired_conversations)
        
        status = {
            "user_id": user_id,
            "retention_policy": privacy_settings.data_retention_policy,
            "retention_days": retention_days,
            "total_conversations": len(conversations),
            "expired_conversations": len(expired_conversations),
            "total_storage_mb": total_storage_mb,
            "expired_storage_mb": expired_storage_mb,
            "next_cleanup_date": (now + timedelta(days=1)).isoformat(),  # Daily cleanup
            "compliance_status": len(expired_conversations) == 0
        }
        
        return status
    
    async def _enforce_user_retention_policy(self, user_id: str) -> Dict[str, Any]:
        """Enforce retention policy for a specific user."""
        privacy_settings = await self._storage.get_privacy_settings(user_id)
        if not privacy_settings:
            return {"deleted_conversations": 0, "archived_conversations": 0}
        
        results = {"deleted_conversations": 0, "archived_conversations": 0}
        
        if privacy_settings.data_retention_policy == DataRetentionPolicy.SESSION_ONLY:
            # Delete all stored conversations
            conversations = await self._storage.get_user_conversations(user_id)
            for conv in conversations:
                await self._storage.delete_conversation(conv.id)
            results["deleted_conversations"] = len(conversations)
            
        elif privacy_settings.data_retention_policy != DataRetentionPolicy.INDEFINITE:
            retention_days = self._get_retention_days(privacy_settings.data_retention_policy)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Get expired conversations
            expired_conversations = await self._storage.get_user_conversations(
                user_id, 
                end_date=cutoff_date
            )
            
            # Archive conversations older than 2x retention period, delete the rest
            archive_cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days * 2)
            
            for conv in expired_conversations:
                if conv.timestamp < archive_cutoff:
                    # Very old - delete completely
                    await self._storage.delete_conversation(conv.id)
                    results["deleted_conversations"] += 1
                else:
                    # Old but not ancient - archive
                    await self._archive_conversation(conv)
                    results["archived_conversations"] += 1
        
        return results
    
    async def _cleanup_user_expired_data(self, user_id: str) -> Dict[str, Any]:
        """Clean up expired data for a specific user."""
        privacy_settings = await self._storage.get_privacy_settings(user_id)
        if not privacy_settings:
            return {"conversations_deleted": 0, "storage_freed_mb": 0}
        
        if privacy_settings.data_retention_policy == DataRetentionPolicy.INDEFINITE:
            return {"conversations_deleted": 0, "storage_freed_mb": 0}
        
        retention_days = self._get_retention_days(privacy_settings.data_retention_policy)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        # Get expired conversations
        expired_conversations = await self._storage.get_user_conversations(
            user_id, 
            end_date=cutoff_date
        )
        
        # Calculate storage to be freed
        storage_freed = sum(self._calculate_conversation_size(conv) for conv in expired_conversations)
        
        # Delete expired conversations
        for conv in expired_conversations:
            await self._storage.delete_conversation(conv.id)
        
        return {
            "conversations_deleted": len(expired_conversations),
            "storage_freed_mb": storage_freed
        }
    
    async def _archive_conversation(self, conversation: Conversation) -> None:
        """Archive a conversation (compress and mark as archived)."""
        # In a real implementation, this would:
        # 1. Compress the conversation data
        # 2. Move it to archive storage (e.g., cold storage)
        # 3. Update the conversation record with archive status
        # 4. Remove from active storage
        
        # For now, we'll just delete it from active storage
        # In production, you'd implement proper archival
        await self._storage.delete_conversation(conversation.id)
        
        logger.info(f"Archived conversation {conversation.id} for user {conversation.user_id}")
    
    async def _optimize_conversation(self, conversation: Conversation) -> Tuple[Conversation, int]:
        """Optimize a conversation by removing duplicates and compressing content."""
        # Simple deduplication - remove duplicate messages
        seen_content = set()
        optimized_messages = []
        deduplicated_count = 0
        
        for message in conversation.messages:
            content_hash = hash(message.content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                optimized_messages.append(message)
            else:
                deduplicated_count += 1
        
        # Create optimized conversation
        optimized_conversation = Conversation(
            id=conversation.id,
            user_id=conversation.user_id,
            timestamp=conversation.timestamp,
            messages=optimized_messages,
            summary=conversation.summary,
            tags=conversation.tags,
            metadata=conversation.metadata
        )
        
        return optimized_conversation, deduplicated_count
    
    def _calculate_conversation_size(self, conversation: Conversation) -> float:
        """Calculate approximate size of a conversation in MB."""
        # Simple size calculation based on content length
        total_chars = 0
        
        # Count message content
        for message in conversation.messages:
            total_chars += len(message.content)
        
        # Count summary and metadata
        if conversation.summary:
            total_chars += len(conversation.summary)
        
        if conversation.metadata:
            total_chars += len(str(conversation.metadata))
        
        # Approximate 1 character = 1 byte, convert to MB
        return total_chars / (1024 * 1024)
    
    def _get_retention_days(self, policy: DataRetentionPolicy) -> int:
        """Get the number of days for a retention policy."""
        policy_days = {
            DataRetentionPolicy.DAYS_30: 30,
            DataRetentionPolicy.DAYS_90: 90,
            DataRetentionPolicy.DAYS_365: 365,
            DataRetentionPolicy.SESSION_ONLY: 0,
            DataRetentionPolicy.INDEFINITE: -1  # -1 means no limit
        }
        return policy_days.get(policy, 90)  # Default to 90 days
    
    async def _get_all_user_ids(self) -> List[str]:
        """Get all user IDs that have data in the system."""
        # This would need to be implemented in the storage layer
        # For now, return empty list as placeholder
        # In production, this would query the database for all unique user_ids
        return []
    
    async def _audit_retention_enforcement(self, results: Dict[str, Any]) -> None:
        """Audit log for retention policy enforcement."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "RETENTION_POLICY_ENFORCEMENT",
            "details": results,
            "source": "data_retention_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _audit_cleanup_operation(self, results: Dict[str, Any]) -> None:
        """Audit log for cleanup operations."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "DATA_CLEANUP",
            "details": results,
            "source": "data_retention_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _audit_archival_operation(self, user_id: str, results: Dict[str, Any]) -> None:
        """Audit log for archival operations."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "operation": "DATA_ARCHIVAL",
            "details": results,
            "source": "data_retention_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _audit_optimization_operation(self, user_id: str, results: Dict[str, Any]) -> None:
        """Audit log for storage optimization operations."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "operation": "STORAGE_OPTIMIZATION",
            "details": results,
            "source": "data_retention_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            await self.initialize()