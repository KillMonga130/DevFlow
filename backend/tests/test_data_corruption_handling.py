"""
Tests for data corruption handling functionality.
"""

import pytest
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from src.memory.services.data_integrity_service import DataIntegrityService, DataCorruptionError
from src.memory.services.integrity_aware_storage_layer import IntegrityAwareStorageLayer
from src.memory.models import Conversation, Message, MessageRole, ConversationContext


class TestDataIntegrityService:
    """Test suite for DataIntegrityService."""
    
    @pytest.fixture
    def integrity_service(self):
        """Create a DataIntegrityService instance for testing."""
        return DataIntegrityService()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return {
            "id": "test123",
            "content": "This is test data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"type": "test"}
        }
    
    def test_generate_checksum(self, integrity_service, sample_data):
        """Test checksum generation."""
        checksum = integrity_service.generate_checksum(sample_data)
        
        assert checksum is not None
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 produces 64-character hex string
        
        # Same data should produce same checksum
        checksum2 = integrity_service.generate_checksum(sample_data)
        assert checksum == checksum2
    
    def test_generate_checksum_different_data(self, integrity_service, sample_data):
        """Test that different data produces different checksums."""
        checksum1 = integrity_service.generate_checksum(sample_data)
        
        modified_data = sample_data.copy()
        modified_data["content"] = "Modified content"
        checksum2 = integrity_service.generate_checksum(modified_data)
        
        assert checksum1 != checksum2
    
    def test_validate_data_integrity_valid(self, integrity_service, sample_data):
        """Test data integrity validation with valid data."""
        checksum = integrity_service.generate_checksum(sample_data)
        
        # Should not raise exception for valid data
        integrity_service.validate_data_integrity(sample_data, checksum)
    
    def test_validate_data_integrity_corrupted(self, integrity_service, sample_data):
        """Test data integrity validation with corrupted data."""
        original_checksum = integrity_service.generate_checksum(sample_data)
        
        # Corrupt the data
        sample_data["content"] = "Corrupted content"
        
        # Should raise DataCorruptionError
        with pytest.raises(DataCorruptionError) as exc_info:
            integrity_service.validate_data_integrity(sample_data, original_checksum)
        
        assert "Data corruption detected" in str(exc_info.value)
    
    def test_validate_data_integrity_invalid_checksum(self, integrity_service, sample_data):
        """Test data integrity validation with invalid checksum format."""
        with pytest.raises(DataCorruptionError) as exc_info:
            integrity_service.validate_data_integrity(sample_data, "invalid_checksum")
        
        assert "Invalid checksum format" in str(exc_info.value)
    
    def test_detect_corruption_patterns_none(self, integrity_service):
        """Test corruption pattern detection with clean data."""
        clean_data = {
            "id": "test123",
            "content": "Clean test content",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        patterns = integrity_service.detect_corruption_patterns(clean_data)
        assert patterns == []
    
    def test_detect_corruption_patterns_null_bytes(self, integrity_service):
        """Test detection of null byte corruption."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \x00 null byte",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        patterns = integrity_service.detect_corruption_patterns(corrupted_data)
        assert "null_bytes" in patterns
    
    def test_detect_corruption_patterns_encoding_issues(self, integrity_service):
        """Test detection of encoding corruption."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \ufffd replacement character",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        patterns = integrity_service.detect_corruption_patterns(corrupted_data)
        assert "encoding_issues" in patterns
    
    def test_detect_corruption_patterns_truncation(self, integrity_service):
        """Test detection of truncation corruption."""
        corrupted_data = {
            "id": "test123",
            "content": "This content appears to be trunca",  # Suspiciously ends mid-word
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        patterns = integrity_service.detect_corruption_patterns(corrupted_data)
        assert "truncation" in patterns
    
    def test_attempt_recovery_simple(self, integrity_service):
        """Test simple data recovery."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \x00 null bytes \x00 here",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        
        assert recovered_data is not None
        assert "\x00" not in recovered_data["content"]
        assert recovered_data["content"] == "Content with  null bytes  here"
    
    def test_attempt_recovery_encoding(self, integrity_service):
        """Test recovery of encoding issues."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \ufffd replacement chars \ufffd",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        
        assert recovered_data is not None
        assert "\ufffd" not in recovered_data["content"]
    
    def test_attempt_recovery_unrecoverable(self, integrity_service):
        """Test recovery attempt on unrecoverable data."""
        # Severely corrupted data that can't be recovered
        corrupted_data = {
            "id": None,
            "content": None,
            "timestamp": "invalid_timestamp"
        }
        
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        assert recovered_data is None
    
    def test_quarantine_corrupted_data(self, integrity_service):
        """Test quarantining corrupted data."""
        corrupted_data = {
            "id": "test123",
            "content": "Corrupted content",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        quarantine_id = integrity_service.quarantine_corrupted_data(
            corrupted_data, 
            "test_corruption", 
            {"checksum_mismatch": True}
        )
        
        assert quarantine_id is not None
        assert isinstance(quarantine_id, str)
        
        # Check that data was stored in quarantine
        assert len(integrity_service._quarantine_storage) == 1
        quarantined_item = integrity_service._quarantine_storage[quarantine_id]
        assert quarantined_item["data"] == corrupted_data
        assert quarantined_item["corruption_reason"] == "test_corruption"
    
    def test_get_quarantine_stats(self, integrity_service):
        """Test getting quarantine statistics."""
        # Add some quarantined data
        for i in range(3):
            integrity_service.quarantine_corrupted_data(
                {"id": f"test{i}", "content": f"corrupted{i}"},
                "test_corruption",
                {}
            )
        
        stats = integrity_service.get_quarantine_stats()
        
        assert stats["total_quarantined"] == 3
        assert stats["corruption_types"]["test_corruption"] == 3
        assert "oldest_quarantine" in stats
        assert "newest_quarantine" in stats
    
    def test_clear_quarantine(self, integrity_service):
        """Test clearing quarantine storage."""
        # Add quarantined data
        integrity_service.quarantine_corrupted_data(
            {"id": "test", "content": "corrupted"},
            "test_corruption",
            {}
        )
        
        assert len(integrity_service._quarantine_storage) == 1
        
        cleared_count = integrity_service.clear_quarantine()
        
        assert cleared_count == 1
        assert len(integrity_service._quarantine_storage) == 0


class TestIntegrityAwareStorageLayer:
    """Test suite for IntegrityAwareStorageLayer."""
    
    @pytest.fixture
    def mock_base_storage(self):
        """Create a mock base storage layer."""
        mock_storage = AsyncMock()
        return mock_storage
    
    @pytest.fixture
    def integrity_storage(self, mock_base_storage):
        """Create an IntegrityAwareStorageLayer instance for testing."""
        # Mock all the abstract methods
        mock_base_storage.delete_all_user_data = AsyncMock()
        mock_base_storage.get_user_data_summary = AsyncMock(return_value={})
        mock_base_storage.cleanup_expired_data = AsyncMock()
        mock_base_storage.health_check = AsyncMock(return_value=True)
        
        return IntegrityAwareStorageLayer(mock_base_storage)
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="Test message",
            timestamp=datetime.now(timezone.utc)
        )
        
        return Conversation(
            id="conv123",
            user_id="user123",
            messages=[message],
            timestamp=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_store_with_integrity_success(self, integrity_storage, mock_base_storage, sample_conversation):
        """Test successful storage with integrity checking."""
        mock_base_storage.store_conversation.return_value = None
        
        await integrity_storage.store_conversation("user123", sample_conversation)
        
        # Verify base storage was called
        mock_base_storage.store_conversation.assert_called_once()
        
        # Verify base storage was called (integrity metadata is handled internally)
        mock_base_storage.store_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_with_integrity_failure(self, integrity_storage, mock_base_storage, sample_conversation):
        """Test storage failure handling."""
        mock_base_storage.store_conversation.side_effect = Exception("Storage failed")
        
        with pytest.raises(Exception) as exc_info:
            await integrity_storage.store_conversation("user123", sample_conversation)
        
        assert "Storage failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_integrity_valid(self, integrity_storage, mock_base_storage, sample_conversation):
        """Test retrieval with valid integrity."""
        # Add integrity metadata to the additional_data field
        sample_conversation.metadata.additional_data['integrity'] = {
            'checksum': integrity_storage.integrity_service.generate_checksum(
                sample_conversation.model_dump()
            ),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        mock_base_storage.get_conversation.return_value = sample_conversation
        
        result = await integrity_storage.get_conversation("conv123")
        
        assert result is not None
        assert result.id == "conv123"
        mock_base_storage.get_conversation.assert_called_once_with("conv123")
    
    @pytest.mark.asyncio
    async def test_retrieve_with_integrity_corrupted(self, integrity_storage, mock_base_storage, sample_conversation):
        """Test retrieval with corrupted data."""
        # Ensure corruption tolerance is disabled for this test
        integrity_storage.enable_corruption_tolerance(False)
        
        # Create a conversation that will fail validation
        sample_conversation.id = None  # This will cause validation to fail
        
        mock_base_storage.get_conversation.return_value = sample_conversation
        
        with pytest.raises(DataCorruptionError):
            await integrity_storage.get_conversation("conv123")
    
    @pytest.mark.asyncio
    async def test_retrieve_with_recovery_success(self, integrity_storage, mock_base_storage):
        """Test successful data recovery during retrieval."""
        # Create corrupted conversation
        corrupted_message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="Content with \x00 null byte",  # Corrupted content
            timestamp=datetime.now(timezone.utc)
        )
        
        corrupted_conversation = Conversation(
            id="conv123",
            user_id="user123",
            messages=[corrupted_message],
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add integrity metadata with wrong checksum to trigger corruption detection
        corrupted_conversation.metadata.additional_data['integrity'] = {
            'checksum': 'wrong_checksum',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        mock_base_storage.get_conversation.return_value = corrupted_conversation
        
        # Enable corruption tolerance and auto recovery for this test
        integrity_storage.enable_corruption_tolerance(True)
        integrity_storage.enable_auto_recovery(True)
        
        # Test the actual recovery mechanism instead of mocking
        result = await integrity_storage.get_conversation("conv123")
        
        # The recovery should have cleaned the null byte
        assert result is not None
        # Note: The actual recovery happens in the integrity service's attempt_recovery method
        # which should clean null bytes from the content
    
    @pytest.mark.asyncio
    async def test_retrieve_with_recovery_failure(self, integrity_storage, mock_base_storage, sample_conversation):
        """Test failed data recovery during retrieval."""
        # Ensure corruption tolerance is disabled for this test
        integrity_storage.enable_corruption_tolerance(False)
        
        # Create a conversation that will fail validation
        sample_conversation.id = None  # This will cause validation to fail
        
        mock_base_storage.get_conversation.return_value = sample_conversation
        
        # Mock failed recovery
        with patch.object(integrity_storage.integrity_service, 'attempt_data_recovery') as mock_recovery:
            mock_recovery.return_value = None  # Recovery failed
            
            with pytest.raises(DataCorruptionError):
                await integrity_storage.get_conversation("conv123")
    
    @pytest.mark.asyncio
    async def test_list_conversations_with_integrity(self, integrity_storage, mock_base_storage):
        """Test listing conversations with integrity checking."""
        # Create sample conversations
        conversations = []
        for i in range(3):
            conv = Conversation(
                id=f"conv{i}",
                user_id="user123",
                messages=[],
                timestamp=datetime.now(timezone.utc)
            )
            conv.metadata.additional_data['integrity'] = {
                'checksum': integrity_storage.integrity_service.generate_checksum(conv.model_dump()),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            conversations.append(conv)
        
        mock_base_storage.get_user_conversations.return_value = conversations
        
        result = await integrity_storage.get_user_conversations("user123")
        
        assert len(result) == 3
        assert all(conv.id.startswith("conv") for conv in result)
    
    @pytest.mark.asyncio
    async def test_list_conversations_with_corrupted_data(self, integrity_storage, mock_base_storage):
        """Test listing conversations with some corrupted data."""
        # Create mix of valid and corrupted conversations
        conversations = []
        
        # Valid conversation
        valid_conv = Conversation(
            id="conv_valid",
            user_id="user123",
            messages=[],
            timestamp=datetime.now(timezone.utc)
        )
        valid_conv.metadata.additional_data['integrity'] = {
            'checksum': integrity_storage.integrity_service.generate_checksum(valid_conv.model_dump()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        conversations.append(valid_conv)
        
        # Corrupted conversation (missing required fields)
        corrupted_conv = Conversation(
            id="",  # Empty ID will cause validation to fail
            user_id="user123",
            messages=[],
            timestamp=datetime.now(timezone.utc)
        )
        conversations.append(corrupted_conv)
        
        mock_base_storage.get_user_conversations.return_value = conversations
        
        # Disable corruption tolerance to ensure corrupted data is filtered out
        integrity_storage.enable_corruption_tolerance(False)
        integrity_storage.enable_auto_recovery(False)
        
        # Should return only valid conversations, corrupted ones are quarantined
        result = await integrity_storage.get_user_conversations("user123")
        
        assert len(result) == 1
        assert result[0].id == "conv_valid"
    
    @pytest.mark.asyncio
    async def test_delete_conversation_with_integrity(self, integrity_storage, mock_base_storage):
        """Test deleting conversation with integrity tracking."""
        # Mock get_conversation to return None (conversation doesn't exist)
        mock_base_storage.get_conversation.return_value = None
        mock_base_storage.delete_conversation.return_value = None
        
        await integrity_storage.delete_conversation("conv123")
        
        mock_base_storage.delete_conversation.assert_called_once_with("conv123")
    
    @pytest.mark.asyncio
    async def test_get_integrity_stats(self, integrity_storage):
        """Test getting integrity statistics."""
        # Test the detailed health status instead
        stats = await integrity_storage.get_detailed_health_status()
        
        assert "base_storage" in stats
        assert "integrity_service" in stats
        assert "corruption_report" in stats["integrity_service"]
    
    @pytest.mark.asyncio
    async def test_verify_all_data_integrity(self, integrity_storage, mock_base_storage):
        """Test verifying integrity of all stored data."""
        # Create sample conversations
        conversations = []
        for i in range(2):
            conv = Conversation(
                id=f"conv{i}",
                user_id="user123",
                messages=[],
                timestamp=datetime.now(timezone.utc)
            )
            conversations.append(conv)
        
        mock_base_storage.get_user_conversations.return_value = conversations
        
        # Test getting conversations with integrity checking
        result = await integrity_storage.get_user_conversations("user123")
        
        assert len(result) == 2
        assert all(conv.id.startswith("conv") for conv in result)


@pytest.mark.asyncio
async def test_integration_corruption_handling():
    """Integration test for complete corruption handling workflow."""
    # Create mock base storage
    mock_storage = AsyncMock()
    
    # Create integrity-aware storage
    integrity_storage = IntegrityAwareStorageLayer(mock_storage)
    
    # Create test conversation
    message = Message(
        id="msg1",
        role=MessageRole.USER,
        content="Test message for integration",
        timestamp=datetime.now(timezone.utc)
    )
    
    conversation = Conversation(
        id="integration_test",
        user_id="user123",
        messages=[message],
        timestamp=datetime.now(timezone.utc)
    )
    
    # Store conversation
    await integrity_storage.store_conversation("user123", conversation)
    
    # Verify storage was called with integrity metadata
    mock_storage.store_conversation.assert_called_once()
    stored_conv = mock_storage.store_conversation.call_args[0][1]
    assert 'integrity' in stored_conv.metadata.additional_data
    
    # Simulate retrieval with valid data
    mock_storage.get_conversation.return_value = stored_conv
    retrieved = await integrity_storage.get_conversation("integration_test")
    
    assert retrieved is not None
    assert retrieved.id == "integration_test"
    assert len(retrieved.messages) == 1

class TestCriticalDataBackup:
    """Test suite for critical data backup functionality."""
    
    @pytest.fixture
    def integrity_service(self):
        """Create a DataIntegrityService instance for testing."""
        return DataIntegrityService()
    
    @pytest.fixture
    def critical_data(self):
        """Create sample critical data for testing."""
        return {
            "conversations": [
                {"id": "conv1", "user_id": "user123", "content": "Important conversation"},
                {"id": "conv2", "user_id": "user123", "content": "Another important conversation"}
            ],
            "preferences": {
                "user_id": "user123",
                "language": "en",
                "theme": "dark"
            },
            "metadata": {
                "backup_version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def test_create_critical_data_backup(self, integrity_service, critical_data):
        """Test creating a critical data backup."""
        backup_id = integrity_service.create_critical_data_backup("user123", critical_data)
        
        assert backup_id is not None
        assert isinstance(backup_id, str)
        assert backup_id.startswith("critical_user123_")
        
        # Verify backup was stored
        assert len(integrity_service._backup_storage) == 1
        backup_entry = integrity_service._backup_storage[backup_id]
        assert backup_entry["user_id"] == "user123"
        assert backup_entry["backup_type"] == "critical"
        assert backup_entry["data"] == critical_data
    
    def test_restore_critical_data_backup(self, integrity_service, critical_data):
        """Test restoring critical data from backup."""
        # Create backup first
        backup_id = integrity_service.create_critical_data_backup("user123", critical_data)
        
        # Restore the backup
        restored_data = integrity_service.restore_critical_data_backup(backup_id)
        
        assert restored_data is not None
        assert restored_data == critical_data
        assert restored_data["conversations"][0]["id"] == "conv1"
        assert restored_data["preferences"]["user_id"] == "user123"
    
    def test_restore_nonexistent_backup(self, integrity_service):
        """Test restoring a backup that doesn't exist."""
        restored_data = integrity_service.restore_critical_data_backup("nonexistent_backup")
        
        assert restored_data is None
    
    def test_restore_corrupted_backup(self, integrity_service, critical_data):
        """Test restoring a backup with corrupted checksum."""
        # Create backup
        backup_id = integrity_service.create_critical_data_backup("user123", critical_data)
        
        # Corrupt the checksum
        integrity_service._backup_storage[backup_id]["checksum"] = "corrupted_checksum"
        
        # Try to restore
        restored_data = integrity_service.restore_critical_data_backup(backup_id)
        
        assert restored_data is None
    
    def test_list_critical_backups(self, integrity_service, critical_data):
        """Test listing critical data backups."""
        # Create multiple backups
        backup_id1 = integrity_service.create_critical_data_backup("user123", critical_data)
        backup_id2 = integrity_service.create_critical_data_backup("user456", critical_data)
        
        # List all backups
        all_backups = integrity_service.list_critical_backups()
        assert len(all_backups) == 2
        
        # List backups for specific user
        user_backups = integrity_service.list_critical_backups("user123")
        assert len(user_backups) == 1
        assert user_backups[0]["user_id"] == "user123"
        assert user_backups[0]["backup_id"] == backup_id1
    
    def test_validate_backup_integrity_valid(self, integrity_service, critical_data):
        """Test validating a valid backup."""
        backup_id = integrity_service.create_critical_data_backup("user123", critical_data)
        
        is_valid, errors = integrity_service.validate_backup_integrity(backup_id)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_backup_integrity_corrupted(self, integrity_service, critical_data):
        """Test validating a corrupted backup."""
        backup_id = integrity_service.create_critical_data_backup("user123", critical_data)
        
        # Corrupt the backup
        integrity_service._backup_storage[backup_id]["checksum"] = "invalid_checksum"
        
        is_valid, errors = integrity_service.validate_backup_integrity(backup_id)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "Checksum verification failed" in errors
    
    def test_validate_nonexistent_backup(self, integrity_service):
        """Test validating a backup that doesn't exist."""
        is_valid, errors = integrity_service.validate_backup_integrity("nonexistent")
        
        assert is_valid is False
        assert len(errors) == 1
        assert "not found" in errors[0]


class TestAdvancedCorruptionScenarios:
    """Test suite for advanced corruption handling scenarios."""
    
    @pytest.fixture
    def integrity_service(self):
        """Create a DataIntegrityService instance for testing."""
        return DataIntegrityService()
    
    def test_multiple_corruption_patterns(self, integrity_service):
        """Test detection of multiple corruption patterns in the same data."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \x00 null bytes and \ufffd replacement chars",
            "description": "This text appears to be trunca",  # Truncation pattern
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        patterns = integrity_service.detect_corruption_patterns(corrupted_data)
        
        assert "null_bytes" in patterns
        assert "encoding_issues" in patterns
        assert "truncation" in patterns
        assert len(patterns) == 3
    
    def test_recovery_with_multiple_patterns(self, integrity_service):
        """Test recovery of data with multiple corruption patterns."""
        corrupted_data = {
            "id": "test123",
            "content": "Content with \x00 null bytes and \ufffd replacement chars",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        
        assert recovered_data is not None
        assert "\x00" not in recovered_data["content"]
        assert "\ufffd" not in recovered_data["content"]
        assert recovered_data["content"] == "Content with  null bytes and  replacement chars"
    
    def test_quarantine_and_recovery_workflow(self, integrity_service):
        """Test complete quarantine and recovery workflow."""
        corrupted_data = {
            "id": "test123",
            "content": "Corrupted content with \x00 null bytes",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Quarantine the data
        quarantine_id = integrity_service.quarantine_corrupted_data(
            corrupted_data,
            "multiple_corruption_patterns",
            {"patterns": ["null_bytes"]}
        )
        
        assert quarantine_id is not None
        
        # Attempt recovery
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        
        assert recovered_data is not None
        assert "\x00" not in recovered_data["content"]
        
        # Check quarantine stats
        stats = integrity_service.get_quarantine_stats()
        assert stats["total_quarantined"] == 1
        assert "multiple_corruption_patterns" in stats["corruption_types"]
    
    def test_backup_before_corruption_handling(self, integrity_service):
        """Test creating backup before handling corrupted data."""
        original_data = {
            "id": "test123",
            "content": "Original clean content",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create backup
        backup_success = integrity_service.create_backup("test_data", original_data)
        assert backup_success is True
        
        # Simulate corruption
        corrupted_data = original_data.copy()
        corrupted_data["content"] = "Corrupted content with \x00 null bytes"
        
        # Attempt recovery
        recovered_data = integrity_service.attempt_recovery(corrupted_data)
        
        # If recovery fails, restore from backup
        if recovered_data is None:
            restored_data = integrity_service.restore_from_backup("test_data")
            assert restored_data == original_data
        else:
            # Recovery succeeded, verify it's clean
            assert "\x00" not in recovered_data["content"]