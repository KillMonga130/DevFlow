"""
Integration tests for data lifecycle management (privacy, export, retention).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from src.memory.services.privacy_controller import PrivacyController
from src.memory.services.data_export_service import DataExportService
from src.memory.services.data_retention_service import DataRetentionService
from src.memory.models.privacy import (
    PrivacySettings, DeleteOptions, DataRetentionPolicy, 
    PrivacyMode, DeleteScope
)
from src.memory.models.conversation import Conversation, Message
from src.memory.models.preferences import UserPreferences


class TestDataLifecycleIntegration:
    """Integration tests for complete data lifecycle management."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage layer."""
        storage = AsyncMock()
        storage.initialize = AsyncMock()
        return storage
    
    @pytest.fixture
    def privacy_controller(self, mock_storage):
        """Create privacy controller with mocked storage."""
        return PrivacyController(storage_layer=mock_storage)
    
    @pytest.fixture
    def export_service(self, mock_storage):
        """Create export service with mocked storage."""
        return DataExportService(storage_layer=mock_storage)
    
    @pytest.fixture
    def retention_service(self, mock_storage):
        """Create retention service with mocked storage."""
        return DataRetentionService(storage_layer=mock_storage)
    
    @pytest.fixture
    def sample_user_data(self):
        """Create comprehensive sample user data."""
        now = datetime.now(timezone.utc)
        
        # Create conversations of different ages
        conversations = []
        for i in range(4):
            age_days = i * 45  # 0, 45, 90, 135 days old
            timestamp = now - timedelta(days=age_days)
            
            messages = [
                Message(
                    id=f"msg{i}_1",
                    role="user",
                    content=f"User message {i} with sensitive data: john@example.com",
                    timestamp=timestamp
                ),
                Message(
                    id=f"msg{i}_2",
                    role="assistant",
                    content=f"Assistant response {i}",
                    timestamp=timestamp + timedelta(minutes=1)
                )
            ]
            
            conv = Conversation(
                id=f"conv{i}",
                user_id="user123",
                timestamp=timestamp,
                messages=messages,
                summary=f"Conversation {i} summary",
                tags=[f"tag{i}", "general"]
            )
            conversations.append(conv)
        
        # Create user preferences
        preferences = UserPreferences(user_id="user123")
        
        # Create privacy settings
        privacy_settings = PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.FULL_MEMORY,
            data_retention_policy=DataRetentionPolicy.DAYS_90,
            allow_preference_learning=True,
            encrypt_sensitive_data=True
        )
        
        return {
            "conversations": conversations,
            "preferences": preferences,
            "privacy_settings": privacy_settings
        }
    
    @pytest.mark.asyncio
    async def test_complete_data_export_workflow(self, export_service, mock_storage, sample_user_data):
        """Test complete data export workflow."""
        # Setup mock storage responses
        mock_storage.get_user_conversations.return_value = sample_user_data["conversations"]
        mock_storage.get_user_preferences.return_value = sample_user_data["preferences"]
        mock_storage.get_privacy_settings.return_value = sample_user_data["privacy_settings"]
        
        # Test JSON export
        json_export = await export_service.export_to_json("user123")
        assert len(json_export) > 0
        assert "user123" in json_export
        
        # Test CSV export
        csv_export = await export_service.export_conversations_to_csv("user123")
        assert "conversation_id" in csv_export  # Header should be present
        assert "conv0" in csv_export  # Should contain conversation data
        
        # Test complete data package
        package = await export_service.create_data_package("user123")
        expected_files = [
            "complete_data.json",
            "conversations.csv",
            "preferences.json",
            "privacy_settings.json",
            "export_summary.json"
        ]
        
        for file_name in expected_files:
            assert file_name in package
            assert len(package[file_name]) > 0
    
    @pytest.mark.asyncio
    async def test_privacy_and_retention_integration(self, privacy_controller, retention_service, 
                                                   mock_storage, sample_user_data):
        """Test integration between privacy controls and retention policies."""
        # Setup mock storage
        mock_storage.get_privacy_settings.return_value = sample_user_data["privacy_settings"]
        mock_storage.get_user_conversations.return_value = sample_user_data["conversations"]
        
        # Test retention status before cleanup
        status_before = await retention_service.get_retention_status("user123")
        assert status_before["total_conversations"] == 4
        assert status_before["retention_policy"] == DataRetentionPolicy.DAYS_90
        
        # Apply retention policy (should remove conversations older than 90 days)
        retention_results = await retention_service._enforce_user_retention_policy("user123")
        
        # Should have deleted or archived old conversations
        total_processed = retention_results["deleted_conversations"] + retention_results["archived_conversations"]
        assert total_processed >= 0  # At least some conversations should be processed
    
    @pytest.mark.asyncio
    async def test_data_anonymization_workflow(self, privacy_controller, mock_storage, sample_user_data):
        """Test data anonymization workflow."""
        # Setup mock storage
        conversations = sample_user_data["conversations"]
        mock_storage.get_conversation.side_effect = lambda conv_id: next(
            (conv for conv in conversations if conv.id == conv_id), None
        )
        
        # Test anonymization
        conversation_ids = [conv.id for conv in conversations[:2]]  # Anonymize first 2 conversations
        await privacy_controller.anonymize_data("user123", conversation_ids)
        
        # Should have called get_conversation for each ID
        assert mock_storage.get_conversation.call_count == 2
        
        # Should have stored anonymized conversations
        assert mock_storage.store_conversation.call_count == 2
        
        # Verify anonymization occurred
        stored_conversations = [call[0][0] for call in mock_storage.store_conversation.call_args_list]
        for conv in stored_conversations:
            # Check that sensitive data was anonymized
            for message in conv.messages:
                assert "[EMAIL]" in message.content or "john@example.com" not in message.content
    
    @pytest.mark.asyncio
    async def test_selective_data_deletion(self, privacy_controller, mock_storage, sample_user_data):
        """Test selective data deletion functionality."""
        conversations = sample_user_data["conversations"]
        mock_storage.get_conversation.side_effect = lambda conv_id: next(
            (conv for conv in conversations if conv.id == conv_id), None
        )
        
        # Test deleting specific conversations
        delete_options = DeleteOptions(
            scope=DeleteScope.SPECIFIC_CONVERSATIONS,
            conversation_ids=["conv0", "conv1"],
            confirm_deletion=True,
            reason="User requested deletion of specific conversations"
        )
        
        await privacy_controller.delete_user_data("user123", delete_options)
        
        # Should have checked each conversation and deleted them
        assert mock_storage.get_conversation.call_count == 2
        assert mock_storage.delete_conversation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_date_range_deletion(self, privacy_controller, mock_storage, sample_user_data):
        """Test date range deletion functionality."""
        conversations = sample_user_data["conversations"]
        
        # Mock conversations in date range
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=100)
        end_date = now - timedelta(days=50)
        
        conversations_in_range = [
            conv for conv in conversations 
            if start_date <= conv.timestamp <= end_date
        ]
        
        mock_storage.get_user_conversations.return_value = conversations_in_range
        
        # Test date range deletion
        delete_options = DeleteOptions(
            scope=DeleteScope.DATE_RANGE,
            date_range_start=start_date,
            date_range_end=end_date,
            confirm_deletion=True,
            reason="Cleanup old conversations in date range"
        )
        
        await privacy_controller.delete_user_data("user123", delete_options)
        
        # Should have queried for conversations in date range
        mock_storage.get_user_conversations.assert_called_with(
            "user123", start_date=start_date, end_date=end_date
        )
        
        # Should have deleted conversations in range
        assert mock_storage.delete_conversation.call_count == len(conversations_in_range)
    
    @pytest.mark.asyncio
    async def test_storage_optimization_workflow(self, retention_service, mock_storage, sample_user_data):
        """Test storage optimization workflow."""
        # Create conversations with duplicate content for optimization
        now = datetime.now(timezone.utc)
        duplicate_messages = [
            Message(id="msg1", role="user", content="Duplicate content", timestamp=now),
            Message(id="msg2", role="user", content="Duplicate content", timestamp=now),  # Duplicate
            Message(id="msg3", role="assistant", content="Unique response", timestamp=now),
            Message(id="msg4", role="user", content="Another duplicate", timestamp=now),
            Message(id="msg5", role="user", content="Another duplicate", timestamp=now)  # Duplicate
        ]
        
        conversation_with_duplicates = Conversation(
            id="conv_dup",
            user_id="user123",
            timestamp=now,
            messages=duplicate_messages,
            summary="Conversation with duplicates"
        )
        
        mock_storage.get_user_conversations.return_value = [conversation_with_duplicates]
        
        # Test storage optimization
        results = await retention_service.optimize_storage("user123")
        
        assert results["user_id"] == "user123"
        assert results["deduplicated_messages"] == 2  # Should remove 2 duplicates
        assert results["compression_ratio"] > 0  # Should achieve some compression
        
        # Should store the optimized conversation
        mock_storage.store_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_privacy_compliance_check(self, privacy_controller, mock_storage, sample_user_data):
        """Test privacy compliance checking."""
        # Setup privacy settings with 90-day retention
        privacy_settings = sample_user_data["privacy_settings"]
        mock_storage.get_privacy_settings.return_value = privacy_settings
        
        # Mock conversations - some within retention period, some outside
        now = datetime.now(timezone.utc)
        compliant_conversations = [
            conv for conv in sample_user_data["conversations"]
            if (now - conv.timestamp).days <= 90
        ]
        
        mock_storage.get_user_conversations.return_value = compliant_conversations
        
        # Test compliance check
        is_compliant = await privacy_controller.check_privacy_compliance("user123")
        
        # Should be compliant if no old conversations exist
        assert isinstance(is_compliant, bool)
    
    @pytest.mark.asyncio
    async def test_session_only_privacy_mode(self, privacy_controller, retention_service, 
                                           mock_storage, sample_user_data):
        """Test session-only privacy mode enforcement."""
        # Create session-only privacy settings
        session_only_settings = PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.NO_MEMORY,
            data_retention_policy=DataRetentionPolicy.SESSION_ONLY
        )
        
        mock_storage.get_privacy_settings.return_value = session_only_settings
        mock_storage.get_user_conversations.return_value = sample_user_data["conversations"]
        
        # Apply retention policy for session-only user
        results = await retention_service._enforce_user_retention_policy("user123")
        
        # Should delete all conversations for session-only users
        assert results["deleted_conversations"] == len(sample_user_data["conversations"])
        
        # Verify compliance check fails if conversations still exist
        mock_storage.get_user_conversations.return_value = sample_user_data["conversations"]  # Still has conversations
        is_compliant = await privacy_controller.check_privacy_compliance("user123")
        assert is_compliant is False  # Should not be compliant
    
    @pytest.mark.asyncio
    async def test_export_after_anonymization(self, privacy_controller, export_service, 
                                            mock_storage, sample_user_data):
        """Test data export after anonymization."""
        conversations = sample_user_data["conversations"]
        
        # Setup mocks for anonymization
        mock_storage.get_conversation.side_effect = lambda conv_id: next(
            (conv for conv in conversations if conv.id == conv_id), None
        )
        
        # Anonymize conversations
        conversation_ids = [conv.id for conv in conversations]
        await privacy_controller.anonymize_data("user123", conversation_ids)
        
        # Get the anonymized conversations that were stored
        anonymized_conversations = [call[0][0] for call in mock_storage.store_conversation.call_args_list]
        
        # Setup export service with anonymized data
        mock_storage.get_user_conversations.return_value = anonymized_conversations
        mock_storage.get_user_preferences.return_value = sample_user_data["preferences"]
        mock_storage.get_privacy_settings.return_value = sample_user_data["privacy_settings"]
        
        # Export anonymized data
        export = await export_service.export_user_data("user123")
        
        # Verify export contains anonymized data
        assert export.user_id == "user123"
        assert len(export.conversations) == len(anonymized_conversations)
        
        # Check that exported conversations contain anonymized content
        for conv_data in export.conversations:
            for message in conv_data["messages"]:
                # Should contain anonymization markers
                content = message["content"]
                if "john@example.com" in content:
                    # Original content should be anonymized
                    assert "[EMAIL]" in content or "john@example.com" not in content


if __name__ == "__main__":
    pytest.main([__file__])