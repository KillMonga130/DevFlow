"""
Unit tests for privacy controller functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.memory.services.privacy_controller import PrivacyController
from src.memory.models.privacy import (
    PrivacySettings, DeleteOptions, UserDataExport, DeleteScope,
    DataRetentionPolicy, PrivacyMode
)
from src.memory.models.conversation import Conversation, Message
from src.memory.models.preferences import UserPreferences


class TestPrivacyController:
    """Test cases for PrivacyController."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage layer."""
        storage = AsyncMock()
        storage.initialize = AsyncMock()
        return storage
    
    @pytest.fixture
    def privacy_controller(self, mock_storage):
        """Create a privacy controller with mocked storage."""
        return PrivacyController(storage_layer=mock_storage)
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        messages = [
            Message(
                id="msg1",
                role="user",
                content="Hello, my name is John Doe and my email is john@example.com",
                timestamp=datetime.now(timezone.utc)
            ),
            Message(
                id="msg2",
                role="assistant",
                content="Hello John! How can I help you today?",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        return Conversation(
            id="conv1",
            user_id="user123",
            timestamp=datetime.now(timezone.utc),
            messages=messages,
            summary="User introduced themselves",
            tags=["introduction"]
        )
    
    @pytest.fixture
    def sample_privacy_settings(self):
        """Create sample privacy settings."""
        return PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.FULL_MEMORY,
            data_retention_policy=DataRetentionPolicy.DAYS_90,
            allow_preference_learning=True,
            allow_search_indexing=True
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, privacy_controller, mock_storage):
        """Test privacy controller initialization."""
        await privacy_controller.initialize()
        mock_storage.initialize.assert_called_once()
        assert privacy_controller._initialized
    
    @pytest.mark.asyncio
    async def test_delete_all_user_data(self, privacy_controller, mock_storage):
        """Test deleting all user data."""
        options = DeleteOptions(
            scope=DeleteScope.ALL_DATA,
            confirm_deletion=True,
            reason="User requested account deletion"
        )
        
        await privacy_controller.delete_user_data("user123", options)
        
        mock_storage.delete_all_user_data.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_delete_user_data_requires_confirmation(self, privacy_controller):
        """Test that data deletion requires explicit confirmation."""
        options = DeleteOptions(
            scope=DeleteScope.ALL_DATA,
            confirm_deletion=False
        )
        
        with pytest.raises(ValueError, match="Deletion must be explicitly confirmed"):
            await privacy_controller.delete_user_data("user123", options)
    
    @pytest.mark.asyncio
    async def test_delete_specific_conversations(self, privacy_controller, mock_storage, sample_conversation):
        """Test deleting specific conversations."""
        mock_storage.get_conversation.return_value = sample_conversation
        
        options = DeleteOptions(
            scope=DeleteScope.SPECIFIC_CONVERSATIONS,
            conversation_ids=["conv1", "conv2"],
            confirm_deletion=True
        )
        
        await privacy_controller.delete_user_data("user123", options)
        
        # Should check each conversation belongs to user
        assert mock_storage.get_conversation.call_count == 2
        mock_storage.delete_conversation.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_conversations_by_date_range(self, privacy_controller, mock_storage):
        """Test deleting conversations by date range."""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        mock_storage.get_user_conversations.return_value = [
            MagicMock(id="conv1"),
            MagicMock(id="conv2")
        ]
        
        options = DeleteOptions(
            scope=DeleteScope.DATE_RANGE,
            date_range_start=start_date,
            date_range_end=end_date,
            confirm_deletion=True
        )
        
        await privacy_controller.delete_user_data("user123", options)
        
        mock_storage.get_user_conversations.assert_called_once_with(
            "user123", start_date=start_date, end_date=end_date
        )
        assert mock_storage.delete_conversation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, privacy_controller, mock_storage, sample_conversation):
        """Test exporting user data."""
        mock_preferences = UserPreferences(user_id="user123")
        mock_privacy_settings = PrivacySettings(user_id="user123")
        
        mock_storage.get_user_conversations.return_value = [sample_conversation]
        mock_storage.get_user_preferences.return_value = mock_preferences
        mock_storage.get_privacy_settings.return_value = mock_privacy_settings
        
        export = await privacy_controller.export_user_data("user123")
        
        assert isinstance(export, UserDataExport)
        assert export.user_id == "user123"
        assert len(export.conversations) == 1
        assert export.preferences is not None
        assert export.privacy_settings is not None
        assert export.metadata["total_conversations"] == 1
    
    @pytest.mark.asyncio
    async def test_apply_retention_policy_session_only(self, privacy_controller, mock_storage):
        """Test applying session-only retention policy."""
        settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.SESSION_ONLY
        )
        
        await privacy_controller.apply_retention_policy("user123", settings)
        
        # Should delete all user data for session-only policy
        mock_storage.delete_all_user_data.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_apply_retention_policy_with_days(self, privacy_controller, mock_storage):
        """Test applying retention policy with specific days."""
        settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.DAYS_30
        )
        
        old_conversations = [MagicMock(id="conv1"), MagicMock(id="conv2")]
        mock_storage.get_user_conversations.return_value = old_conversations
        
        await privacy_controller.apply_retention_policy("user123", settings)
        
        # Should query for old conversations and delete them
        mock_storage.get_user_conversations.assert_called_once()
        assert mock_storage.delete_conversation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_anonymize_data(self, privacy_controller, mock_storage, sample_conversation):
        """Test anonymizing conversation data."""
        mock_storage.get_conversation.return_value = sample_conversation
        
        await privacy_controller.anonymize_data("user123", ["conv1"])
        
        mock_storage.get_conversation.assert_called_once_with("conv1")
        mock_storage.store_conversation.assert_called_once()
        
        # Check that the stored conversation has anonymized content
        stored_conv = mock_storage.store_conversation.call_args[0][0]
        assert "[EMAIL]" in stored_conv.messages[0].content
        assert "[NAME]" in stored_conv.messages[0].content
    
    def test_anonymize_text(self, privacy_controller):
        """Test text anonymization functionality."""
        text = "Hello, my name is John Doe and my email is john@example.com. Call me at 555-123-4567."
        
        anonymized = privacy_controller._anonymize_text(text)
        
        assert "[EMAIL]" in anonymized
        assert "[PHONE]" in anonymized
        assert "[NAME]" in anonymized
        assert "john@example.com" not in anonymized
        assert "555-123-4567" not in anonymized
    
    @pytest.mark.asyncio
    async def test_check_privacy_compliance_no_settings(self, privacy_controller, mock_storage):
        """Test privacy compliance check with no settings."""
        mock_storage.get_privacy_settings.return_value = None
        
        is_compliant = await privacy_controller.check_privacy_compliance("user123")
        
        assert is_compliant is True
    
    @pytest.mark.asyncio
    async def test_check_privacy_compliance_retention_violation(self, privacy_controller, mock_storage):
        """Test privacy compliance check with retention policy violation."""
        settings = PrivacySettings(
            user_id="user123",
            data_retention_policy=DataRetentionPolicy.DAYS_30
        )
        
        # Mock old conversations that violate retention policy
        old_conversation = MagicMock()
        mock_storage.get_privacy_settings.return_value = settings
        mock_storage.get_user_conversations.return_value = [old_conversation]
        
        is_compliant = await privacy_controller.check_privacy_compliance("user123")
        
        assert is_compliant is False
    
    @pytest.mark.asyncio
    async def test_check_privacy_compliance_no_memory_violation(self, privacy_controller, mock_storage):
        """Test privacy compliance check with no-memory mode violation."""
        settings = PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.NO_MEMORY
        )
        
        # Mock stored conversations that violate no-memory mode
        conversation = MagicMock()
        mock_storage.get_privacy_settings.return_value = settings
        mock_storage.get_user_conversations.return_value = [conversation]
        
        is_compliant = await privacy_controller.check_privacy_compliance("user123")
        
        assert is_compliant is False
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, privacy_controller):
        """Test audit logging functionality."""
        with patch('src.memory.services.privacy_controller.logger') as mock_logger:
            await privacy_controller.audit_data_access(
                "user123", 
                "TEST_OPERATION", 
                "Test audit log entry"
            )
            
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert "AUDIT:" in log_call
            assert "user123" in log_call
            assert "TEST_OPERATION" in log_call
    
    def test_get_retention_days(self, privacy_controller):
        """Test retention days calculation."""
        assert privacy_controller._get_retention_days(DataRetentionPolicy.DAYS_30) == 30
        assert privacy_controller._get_retention_days(DataRetentionPolicy.DAYS_90) == 90
        assert privacy_controller._get_retention_days(DataRetentionPolicy.DAYS_365) == 365
        assert privacy_controller._get_retention_days(DataRetentionPolicy.INDEFINITE) == 90  # Default
    
    @pytest.mark.asyncio
    async def test_delete_user_data_error_handling(self, privacy_controller, mock_storage):
        """Test error handling in delete_user_data."""
        mock_storage.delete_all_user_data.side_effect = Exception("Database error")
        
        options = DeleteOptions(
            scope=DeleteScope.ALL_DATA,
            confirm_deletion=True
        )
        
        with pytest.raises(Exception, match="Database error"):
            await privacy_controller.delete_user_data("user123", options)
    
    @pytest.mark.asyncio
    async def test_export_user_data_error_handling(self, privacy_controller, mock_storage):
        """Test error handling in export_user_data."""
        mock_storage.get_user_conversations.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await privacy_controller.export_user_data("user123")


if __name__ == "__main__":
    pytest.main([__file__])