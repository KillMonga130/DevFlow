"""
Unit tests for data export service functionality.
"""

import pytest
import json
import csv
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.memory.services.data_export_service import DataExportService
from src.memory.models.conversation import Conversation, Message
from src.memory.models.preferences import UserPreferences
from src.memory.models.privacy import PrivacySettings, DataRetentionPolicy, PrivacyMode


class TestDataExportService:
    """Test cases for DataExportService."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage layer."""
        storage = AsyncMock()
        storage.initialize = AsyncMock()
        return storage
    
    @pytest.fixture
    def export_service(self, mock_storage):
        """Create a data export service with mocked storage."""
        return DataExportService(storage_layer=mock_storage)
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        now = datetime.now(timezone.utc)
        
        conversations = []
        for i in range(3):
            messages = [
                Message(
                    id=f"msg{i}_1",
                    role="user",
                    content=f"User message {i}",
                    timestamp=now - timedelta(minutes=10-i)
                ),
                Message(
                    id=f"msg{i}_2",
                    role="assistant",
                    content=f"Assistant response {i}",
                    timestamp=now - timedelta(minutes=9-i)
                )
            ]
            
            conv = Conversation(
                id=f"conv{i}",
                user_id="user123",
                timestamp=now - timedelta(hours=i),
                messages=messages,
                summary=f"Conversation {i} summary",
                tags=[f"tag{i}", "general"]
            )
            conversations.append(conv)
        
        return conversations
    
    @pytest.fixture
    def sample_preferences(self):
        """Create sample user preferences."""
        return UserPreferences(user_id="user123")
    
    @pytest.fixture
    def sample_privacy_settings(self):
        """Create sample privacy settings."""
        return PrivacySettings(
            user_id="user123",
            privacy_mode=PrivacyMode.FULL_MEMORY,
            data_retention_policy=DataRetentionPolicy.DAYS_90
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, export_service, mock_storage):
        """Test service initialization."""
        await export_service.initialize()
        mock_storage.initialize.assert_called_once()
        assert export_service._initialized
    
    @pytest.mark.asyncio
    async def test_export_user_data_complete(self, export_service, mock_storage, 
                                           sample_conversations, sample_preferences, 
                                           sample_privacy_settings):
        """Test complete user data export."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        mock_storage.get_user_preferences.return_value = sample_preferences
        mock_storage.get_privacy_settings.return_value = sample_privacy_settings
        
        export = await export_service.export_user_data("user123")
        
        assert export.user_id == "user123"
        assert len(export.conversations) == 3
        assert export.preferences is not None
        assert export.privacy_settings is not None
        assert export.metadata is not None
        
        # Check that conversations have computed fields
        assert export.conversations[0]["message_count"] == 2
        assert "duration_minutes" in export.conversations[0]
        assert "participant_roles" in export.conversations[0]
    
    @pytest.mark.asyncio
    async def test_export_user_data_no_metadata(self, export_service, mock_storage, sample_conversations):
        """Test export without metadata."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_privacy_settings.return_value = None
        
        export = await export_service.export_user_data("user123", include_metadata=False)
        
        assert export.metadata == {}
    
    @pytest.mark.asyncio
    async def test_export_to_json(self, export_service, mock_storage, sample_conversations):
        """Test JSON export functionality."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        mock_storage.get_user_preferences.return_value = None
        mock_storage.get_privacy_settings.return_value = None
        
        json_export = await export_service.export_to_json("user123")
        
        # Should be valid JSON
        parsed = json.loads(json_export)
        assert parsed["user_id"] == "user123"
        assert len(parsed["conversations"]) == 3
        
        # Test pretty printing
        pretty_export = await export_service.export_to_json("user123", pretty_print=True)
        assert "\n" in pretty_export  # Should have newlines for pretty printing
    
    @pytest.mark.asyncio
    async def test_export_conversations_to_csv(self, export_service, mock_storage, sample_conversations):
        """Test CSV export for conversations."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        
        csv_export = await export_service.export_conversations_to_csv("user123")
        
        # Parse CSV to verify structure
        csv_reader = csv.reader(StringIO(csv_export))
        rows = list(csv_reader)
        
        # Should have header + 6 message rows (2 messages per conversation * 3 conversations)
        assert len(rows) == 7  # 1 header + 6 data rows
        
        # Check header
        expected_header = [
            'conversation_id', 'timestamp', 'message_id', 'role', 
            'content', 'message_timestamp', 'tags', 'summary'
        ]
        assert rows[0] == expected_header
        
        # Check first data row
        assert rows[1][0] == "conv0"  # conversation_id
        assert rows[1][3] == "user"   # role
        assert "User message 0" in rows[1][4]  # content
    
    @pytest.mark.asyncio
    async def test_export_preferences_to_json(self, export_service, mock_storage, sample_preferences):
        """Test preferences JSON export."""
        mock_storage.get_user_preferences.return_value = sample_preferences
        
        json_export = await export_service.export_preferences_to_json("user123")
        
        parsed = json.loads(json_export)
        assert parsed["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_export_preferences_to_json_no_preferences(self, export_service, mock_storage):
        """Test preferences export when no preferences exist."""
        mock_storage.get_user_preferences.return_value = None
        
        json_export = await export_service.export_preferences_to_json("user123")
        
        parsed = json.loads(json_export)
        assert parsed["user_id"] == "user123"
        assert parsed["preferences"] is None
    
    @pytest.mark.asyncio
    async def test_create_data_package(self, export_service, mock_storage, 
                                     sample_conversations, sample_preferences, 
                                     sample_privacy_settings):
        """Test creating a complete data package."""
        mock_storage.get_user_conversations.return_value = sample_conversations
        mock_storage.get_user_preferences.return_value = sample_preferences
        mock_storage.get_privacy_settings.return_value = sample_privacy_settings
        
        package = await export_service.create_data_package("user123")
        
        # Should contain multiple files
        expected_files = [
            "complete_data.json",
            "conversations.csv", 
            "preferences.json",
            "privacy_settings.json",
            "export_summary.json"
        ]
        
        for file_name in expected_files:
            assert file_name in package
            assert len(package[file_name]) > 0  # Should have content
        
        # Verify export summary
        summary = json.loads(package["export_summary.json"])
        assert summary["user_id"] == "user123"
        assert summary["files_included"] == list(package.keys())
    
    @pytest.mark.asyncio
    async def test_formatted_conversations(self, export_service, sample_conversations):
        """Test conversation formatting for export."""
        formatted = await export_service._get_formatted_conversations("user123")
        
        # Mock the storage call
        export_service._storage.get_user_conversations = AsyncMock(return_value=sample_conversations)
        formatted = await export_service._get_formatted_conversations("user123")
        
        assert len(formatted) == 3
        
        # Check computed fields
        for conv in formatted:
            assert "message_count" in conv
            assert "duration_minutes" in conv
            assert "participant_roles" in conv
            assert conv["message_count"] == 2
            assert "user" in conv["participant_roles"]
            assert "assistant" in conv["participant_roles"]
    
    @pytest.mark.asyncio
    async def test_formatted_preferences(self, export_service, sample_preferences):
        """Test preferences formatting for export."""
        export_service._storage.get_user_preferences = AsyncMock(return_value=sample_preferences)
        
        formatted = await export_service._get_formatted_preferences("user123")
        
        assert formatted is not None
        assert "total_topics" in formatted
        assert "has_communication_preferences" in formatted
    
    @pytest.mark.asyncio
    async def test_formatted_privacy_settings(self, export_service, sample_privacy_settings):
        """Test privacy settings formatting for export."""
        export_service._storage.get_privacy_settings = AsyncMock(return_value=sample_privacy_settings)
        
        formatted = await export_service._get_formatted_privacy_settings("user123")
        
        assert formatted is not None
        assert "memory_enabled" in formatted
        assert "long_term_storage_allowed" in formatted
        assert formatted["memory_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_generate_export_metadata(self, export_service):
        """Test metadata generation."""
        conversations = [
            {
                "id": "conv1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_count": 3,
                "duration_minutes": 5.0,
                "tags": ["tag1", "tag2"]
            },
            {
                "id": "conv2", 
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "message_count": 2,
                "duration_minutes": 3.0,
                "tags": ["tag2", "tag3"]
            }
        ]
        
        preferences = {"user_id": "user123"}
        privacy_settings = {"data_retention_policy": "90_days"}
        search_history = []
        
        metadata = await export_service._generate_export_metadata(
            "user123", conversations, preferences, privacy_settings, search_history
        )
        
        assert "export_info" in metadata
        assert "data_summary" in metadata
        assert "date_range" in metadata
        assert "content_analysis" in metadata
        assert "privacy_info" in metadata
        
        # Check data summary
        assert metadata["data_summary"]["total_conversations"] == 2
        assert metadata["data_summary"]["total_messages"] == 5
        assert metadata["data_summary"]["has_preferences"] is True
        
        # Check content analysis
        assert metadata["content_analysis"]["unique_tags"] == ["tag1", "tag2", "tag3"]
        assert metadata["content_analysis"]["tag_count"] == 3
    
    def test_calculate_conversation_duration(self, export_service, sample_conversations):
        """Test conversation duration calculation."""
        conv = sample_conversations[0]
        duration = export_service._calculate_conversation_duration(conv)
        
        # Should be 1 minute (10-9 = 1 minute difference between messages)
        assert duration == 1.0
    
    def test_calculate_conversation_duration_single_message(self, export_service):
        """Test duration calculation with single message."""
        from src.memory.models.conversation import Conversation, Message
        
        conv = Conversation(
            id="conv1",
            user_id="user123",
            timestamp=datetime.now(timezone.utc),
            messages=[
                Message(
                    id="msg1",
                    role="user",
                    content="Single message",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        )
        
        duration = export_service._calculate_conversation_duration(conv)
        assert duration == 0.0
    
    def test_json_serializer(self, export_service):
        """Test custom JSON serializer."""
        now = datetime.now(timezone.utc)
        
        # Should serialize datetime
        result = export_service._json_serializer(now)
        assert isinstance(result, str)
        assert "T" in result  # ISO format
        
        # Should raise TypeError for unsupported types
        with pytest.raises(TypeError):
            export_service._json_serializer(object())
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, export_service):
        """Test audit logging functionality."""
        with patch('src.memory.services.data_export_service.logger') as mock_logger:
            await export_service._audit_export_request("user123", "json")
            
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert "AUDIT:" in log_call
            assert "DATA_EXPORT_REQUEST" in log_call
    
    @pytest.mark.asyncio
    async def test_export_error_handling(self, export_service, mock_storage):
        """Test error handling in export operations."""
        mock_storage.get_user_conversations.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await export_service.export_user_data("user123")


if __name__ == "__main__":
    pytest.main([__file__])