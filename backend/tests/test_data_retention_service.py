"""
Unit tests for data retention service functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.memory.services.data_retention_service import DataRetentionService
from src.memory.models.privacy import PrivacySettings, DataRetentionPolicy, PrivacyMode
from src.memory.models.conversation import Conversation, Message


class TestDataRetentionService:
    """Test cases for DataRetentionService."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage layer."""
        storage = AsyncMock()
        storage.initialize = AsyncMock()
        return storage
    
    @pytest.fixture
    def mock_privacy_controller(self):
        """Create a mock privacy controller."""
        controller = AsyncMock()
        controller.initialize = AsyncMock()
        return controller
    
    @pytest.fixture
    def retention_service(self, mock_storage, mock_privacy_controller):
        """Create a data retention service with mocked dependencies."""
        return DataRetentionService(
            storage_layer=mock_storage,
            privacy_controller=mock_privacy_controller
        )
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations with different ages."""
        now = datetime.now(timezone.utc)
        
        conversations = []
        for i in range(5):
            # Create conversations with different ages
            age_days = i * 30  # 0, 30, 60, 90, 120 days old
            timestamp = now - timedelta(days=age_days)
            
            messages = [
                Message(
                    id=f"msg{i}_1",
                    role="user",
                    content=f"User message {i}" * 10,  # Make content longer for size calculation
                    timestamp=timestamp
                ),
                Message(
                    id=f"msg{i}_2",
                    role="assistant",
                    content=f"Assistant response {i}" * 10,
                    timestamp=timestamp + timedelta(minutes=1)
                )
            ]
            
            conv = Conversation(
                id=f"conv{i}",
                user_id="user123",
                timestamp=timestamp,
                messages=messages,
                summary=f"Conversation {i} summary",
                tags=[f"tag{i}"]
            )
            conversations.append(conv)
        
        return conversations
    
    @pytest.fixture
    def sample_privacy_settings(self):
        """Create sample privacy settings."""
        return PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.FULL_MEMORY,
            data_retention_policy=DataRetentionPolicy.DAYS_90
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, retention_service, mock_storage, mock_privacy_controller):
        """Test service initialization."""
        await retention_service.initialize()
        
        mock_storage.initialize.assert_called_once()
        mock_privacy_controller.initialize.assert_called_once()
        assert retention_service._initialized
    
    @pytest.mark.asyncio
    async def test_enforce_retention_policies_single_user(self, retention_service, mock_storage, 
                                                        sample_conversations, sample_privacy_settings):
        """Test enforcing retention policies for a single user."""
        # Mock storage responses
        mock_storage.get_privacy_settings.return_value = sample_privacy_settings
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        results = await retention_service.enforce_retention_policies(["user123"])
        
        assert results["processed_users"] == 1
        assert results["deleted_conversations"] >= 0
        assert results["archived_conversations"] >= 0
        assert len(results["errors"]) == 0
        assert results["processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_enforce_retention_policies_session_only(self, retention_service, mock_storage, 
                                                         sample_conversations):
        """Test retention policy enforcement for session-only users."""
        session_only_settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.SESSION_ONLY
        )
        
        mock_storage.get_privacy_settings.return_value = session_only_settings
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        results = await retention_service.enforce_retention_policies(["user123"])
        
        # Should delete all conversations for session-only users
        assert results["deleted_conversations"] == len(sample_conversations)
        assert mock_storage.delete_conversation.call_count == len(sample_conversations)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_data(self, retention_service, mock_storage, sample_conversations):
        """Test cleanup of expired data."""
        # Set up privacy settings with 90-day retention
        privacy_settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.DAYS_90
        )
        
        mock_storage.get_privacy_settings.return_value = privacy_settings
        
        # Mock conversations older than 90 days
        old_conversations = [conv for conv in sample_conversations if 
                           (datetime.now(timezone.utc) - conv.timestamp).days > 90]
        mock_storage.get_user_conversations.return_value = old_conversations
        
        # Mock getting all user IDs
        retention_service._get_all_user_ids = AsyncMock(return_value=["user123"])
        
        results = await retention_service.cleanup_expired_data()
        
        assert results["total_users_processed"] == 1
        assert results["total_conversations_deleted"] == len(old_conversations)
        assert results["storage_freed_mb"] >= 0
    
    @pytest.mark.asyncio
    async def test_archive_old_conversations(self, retention_service, mock_storage, sample_conversations):
        """Test archiving old conversations."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        results = await retention_service.archive_old_conversations("user123", archive_threshold_days=60)
        
        assert results["user_id"] == "user123"
        assert results["archived_conversations"] >= 0
        assert results["archived_size_mb"] >= 0
        assert "cutoff_date" in results
    
    @pytest.mark.asyncio
    async def test_optimize_storage(self, retention_service, mock_storage):
        """Test storage optimization."""
        # Create conversations with duplicate messages
        now = datetime.now(timezone.utc)
        duplicate_messages = [
            Message(id="msg1", role="user", content="Duplicate content", timestamp=now),
            Message(id="msg2", role="user", content="Duplicate content", timestamp=now),  # Duplicate
            Message(id="msg3", role="assistant", content="Unique response", timestamp=now)
        ]
        
        conversation = Conversation(
            id="conv1",
            user_id="user123",
            timestamp=now,
            messages=duplicate_messages,
            summary="Test conversation"
        )
        
        mock_storage.get_user_conversations.return_value = [conversation]
        
        results = await retention_service.optimize_storage("user123")
        
        assert results["user_id"] == "user123"
        assert results["original_size_mb"] >= 0
        assert results["optimized_size_mb"] >= 0
        assert results["compression_ratio"] >= 0
        assert results["deduplicated_messages"] >= 0
        
        # Should store the optimized conversation
        mock_storage.store_conversation.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_retention_status(self, retention_service, mock_storage, 
                                      sample_conversations, sample_privacy_settings):
        """Test getting retention status for a user."""
        mock_storage.get_privacy_settings.return_value = sample_privacy_settings
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        status = await retention_service.get_retention_status("user123")
        
        assert status["user_id"] == "user123"
        assert status["retention_policy"] == DataRetentionPolicy.DAYS_90
        assert status["retention_days"] == 90
        assert status["total_conversations"] == len(sample_conversations)
        assert "expired_conversations" in status
        assert "total_storage_mb" in status
        assert "compliance_status" in status
    
    @pytest.mark.asyncio
    async def test_get_retention_status_no_settings(self, retention_service, mock_storage, sample_conversations):
        """Test getting retention status when user has no privacy settings."""
        mock_storage.get_privacy_settings.return_value = None
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        status = await retention_service.get_retention_status("user123")
        
        # Should use default settings
        assert status["user_id"] == "user123"
        assert status["retention_policy"] == DataRetentionPolicy.DAYS_90  # Default
    
    def test_calculate_conversation_size(self, retention_service):
        """Test conversation size calculation."""
        now = datetime.now(timezone.utc)
        messages = [
            Message(id="msg1", role="user", content="A" * 1000, timestamp=now),
            Message(id="msg2", role="assistant", content="B" * 1000, timestamp=now)
        ]
        
        conversation = Conversation(
            id="conv1",
            user_id="user123",
            timestamp=now,
            messages=messages,
            summary="C" * 100
        )
        
        size_mb = retention_service._calculate_conversation_size(conversation)
        
        # Should be approximately 2.1KB converted to MB
        assert size_mb > 0
        assert size_mb < 1  # Should be much less than 1MB
    
    def test_get_retention_days(self, retention_service):
        """Test retention days calculation."""
        assert retention_service._get_retention_days(DataRetentionPolicy.DAYS_30) == 30
        assert retention_service._get_retention_days(DataRetentionPolicy.DAYS_90) == 90
        assert retention_service._get_retention_days(DataRetentionPolicy.DAYS_365) == 365
        assert retention_service._get_retention_days(DataRetentionPolicy.SESSION_ONLY) == 0
        assert retention_service._get_retention_days(DataRetentionPolicy.INDEFINITE) == -1
    
    @pytest.mark.asyncio
    async def test_optimize_conversation_deduplication(self, retention_service):
        """Test conversation optimization with message deduplication."""
        now = datetime.now(timezone.utc)
        
        # Create conversation with duplicate messages
        messages = [
            Message(id="msg1", role="user", content="Hello", timestamp=now),
            Message(id="msg2", role="user", content="Hello", timestamp=now),  # Duplicate
            Message(id="msg3", role="assistant", content="Hi there", timestamp=now),
            Message(id="msg4", role="user", content="How are you?", timestamp=now),
            Message(id="msg5", role="user", content="How are you?", timestamp=now)  # Duplicate
        ]
        
        conversation = Conversation(
            id="conv1",
            user_id="user123",
            timestamp=now,
            messages=messages
        )
        
        optimized_conv, dedup_count = await retention_service._optimize_conversation(conversation)
        
        # Should remove 2 duplicate messages
        assert dedup_count == 2
        assert len(optimized_conv.messages) == 3  # 5 - 2 duplicates
        assert optimized_conv.id == conversation.id
        assert optimized_conv.user_id == conversation.user_id
    
    @pytest.mark.asyncio
    async def test_enforce_user_retention_policy_indefinite(self, retention_service, mock_storage):
        """Test retention policy enforcement for indefinite retention."""
        indefinite_settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.INDEFINITE
        )
        
        mock_storage.get_privacy_settings.return_value = indefinite_settings
        
        results = await retention_service._enforce_user_retention_policy("user123")
        
        # Should not delete or archive anything for indefinite retention
        assert results["deleted_conversations"] == 0
        assert results["archived_conversations"] == 0
    
    @pytest.mark.asyncio
    async def test_enforce_user_retention_policy_no_settings(self, retention_service, mock_storage):
        """Test retention policy enforcement when user has no settings."""
        mock_storage.get_privacy_settings.return_value = None
        
        results = await retention_service._enforce_user_retention_policy("user123")
        
        # Should not delete or archive anything when no settings exist
        assert results["deleted_conversations"] == 0
        assert results["archived_conversations"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_user_expired_data_indefinite(self, retention_service, mock_storage):
        """Test cleanup for user with indefinite retention policy."""
        indefinite_settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.INDEFINITE
        )
        
        mock_storage.get_privacy_settings.return_value = indefinite_settings
        
        results = await retention_service._cleanup_user_expired_data("user123")
        
        # Should not clean up anything for indefinite retention
        assert results["conversations_deleted"] == 0
        assert results["storage_freed_mb"] == 0
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, retention_service):
        """Test audit logging functionality."""
        with patch('src.memory.services.data_retention_service.logger') as mock_logger:
            results = {"test": "data"}
            await retention_service._audit_retention_enforcement(results)
            
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert "AUDIT:" in log_call
            assert "RETENTION_POLICY_ENFORCEMENT" in log_call
    
    @pytest.mark.asyncio
    async def test_error_handling_in_enforcement(self, retention_service, mock_storage):
        """Test error handling during retention policy enforcement."""
        # Mock storage to raise an exception
        mock_storage.get_privacy_settings.side_effect = Exception("Database error")
        
        # Mock getting user IDs
        retention_service._get_all_user_ids = AsyncMock(return_value=["user123"])
        
        results = await retention_service.enforce_retention_policies()
        
        # Should handle the error gracefully
        assert results["processed_users"] == 0
        assert len(results["errors"]) > 0
        assert "Database error" in str(results["errors"])
    
    @pytest.mark.asyncio
    async def test_archive_conversation(self, retention_service, mock_storage):
        """Test conversation archival."""
        now = datetime.now(timezone.utc)
        conversation = Conversation(
            id="conv1",
            user_id="user123",
            timestamp=now,
            messages=[
                Message(id="msg1", role="user", content="Test", timestamp=now)
            ]
        )
        
        await retention_service._archive_conversation(conversation)
        
        # Should delete the conversation (placeholder for actual archival)
        mock_storage.delete_conversation.assert_called_once_with("conv1")


if __name__ == "__main__":
    pytest.main([__file__])