"""
Tests for storage backend implementations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.memory.utils.storage_backends import (
    PostgreSQLStorageBackend, MongoDBStorageBackend, HybridStorageBackend
)
from src.memory.models import (
    Conversation, ConversationSummary, UserPreferences, 
    PrivacySettings, Message
)


class TestPostgreSQLStorageBackend:
    """Tests for PostgreSQL storage backend."""
    
    @pytest.fixture
    def postgres_backend(self):
        with patch('src.memory.utils.storage_backends.get_database_manager') as mock_db_manager:
            mock_manager = AsyncMock()
            mock_manager.postgres = AsyncMock()
            mock_db_manager.return_value = mock_manager
            return PostgreSQLStorageBackend()
    
    @pytest.mark.asyncio
    async def test_initialize(self, postgres_backend):
        """Test PostgreSQL backend initialization."""
        postgres_backend.db_manager.initialize_all = AsyncMock()
        postgres_backend._create_tables = AsyncMock()
        
        await postgres_backend.initialize()
        
        postgres_backend.db_manager.initialize_all.assert_called_once()
        postgres_backend._create_tables.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_user_preferences(self, postgres_backend):
        """Test storing user preferences."""
        preferences = UserPreferences(
            user_id="test_user",
            language="en",
            timezone="UTC",
            communication_style="formal"
        )
        
        postgres_backend.db_manager.postgres.execute_with_retry = AsyncMock()
        
        await postgres_backend.store_user_preferences(preferences)
        
        postgres_backend.db_manager.postgres.execute_with_retry.assert_called_once()
        call_args = postgres_backend.db_manager.postgres.execute_with_retry.call_args
        assert call_args[0][1] == "test_user"  # user_id parameter
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_found(self, postgres_backend):
        """Test getting user preferences when they exist."""
        mock_row = {
            'preferences': '{"user_id": "test_user", "response_style": {"style_type": "conversational", "tone": "helpful"}, "topic_interests": [], "communication_preferences": {"language_preference": "en", "timezone": "UTC"}, "learning_enabled": true, "metadata": {}, "version": 1}'
        }
        postgres_backend.db_manager.postgres.fetch_with_retry = AsyncMock(return_value=[mock_row])
        
        result = await postgres_backend.get_user_preferences("test_user")
        
        assert result is not None
        assert result.user_id == "test_user"
        assert result.communication_preferences.language_preference == "en"
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_not_found(self, postgres_backend):
        """Test getting user preferences when they don't exist."""
        postgres_backend.db_manager.postgres.fetch_with_retry = AsyncMock(return_value=[])
        
        result = await postgres_backend.get_user_preferences("test_user")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_store_privacy_settings(self, postgres_backend):
        """Test storing privacy settings."""
        settings = PrivacySettings(
            user_id="test_user",
            data_retention_days=90,
            allow_analytics=False,
            encryption_enabled=True
        )
        
        postgres_backend.db_manager.postgres.execute_with_retry = AsyncMock()
        
        await postgres_backend.store_privacy_settings(settings)
        
        postgres_backend.db_manager.postgres.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_conversation_summary(self, postgres_backend):
        """Test storing conversation summary."""
        summary = ConversationSummary(
            conversation_id="conv_1",
            timestamp=datetime.now(timezone.utc),
            summary_text="Test conversation summary",
            key_topics=["topic1", "topic2"],
            importance_score=0.8,
            message_count=5
        )
        
        postgres_backend.db_manager.postgres.execute_with_retry = AsyncMock()
        
        await postgres_backend.store_conversation_summary(summary)
        
        postgres_backend.db_manager.postgres.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_summaries(self, postgres_backend):
        """Test getting conversation summaries."""
        mock_rows = [
            {
                'id': 'summary_1',
                'user_id': 'test_user',
                'conversation_id': 'conv_1',
                'summary': 'Test summary',
                'key_topics': ['topic1', 'topic2'],
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        postgres_backend.db_manager.postgres.fetch_with_retry = AsyncMock(return_value=mock_rows)
        
        result = await postgres_backend.get_conversation_summaries("test_user")
        
        assert len(result) == 1
        assert result[0].conversation_id == "conv_1"
    
    @pytest.mark.asyncio
    async def test_delete_all_user_data(self, postgres_backend):
        """Test deleting all user data."""
        postgres_backend.db_manager.postgres.execute_with_retry = AsyncMock()
        
        await postgres_backend.delete_all_user_data("test_user")
        
        # Should be called 3 times (preferences, privacy_settings, conversation_summaries)
        assert postgres_backend.db_manager.postgres.execute_with_retry.call_count == 3
    
    @pytest.mark.asyncio
    async def test_health_check(self, postgres_backend):
        """Test health check."""
        postgres_backend.db_manager.postgres.health_check = AsyncMock(return_value=True)
        
        result = await postgres_backend.health_check()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_conversation_methods_not_implemented(self, postgres_backend):
        """Test that conversation methods raise NotImplementedError."""
        conversation = Conversation(
            id="conv_1",
            user_id="test_user",
            messages=[],
            timestamp=datetime.now(timezone.utc)
        )
        
        with pytest.raises(NotImplementedError):
            await postgres_backend.store_conversation(conversation)
        
        with pytest.raises(NotImplementedError):
            await postgres_backend.get_conversation("conv_1")
        
        with pytest.raises(NotImplementedError):
            await postgres_backend.get_user_conversations("test_user")
        
        with pytest.raises(NotImplementedError):
            await postgres_backend.delete_conversation("conv_1")


class TestMongoDBStorageBackend:
    """Tests for MongoDB storage backend."""
    
    @pytest.fixture
    def mongodb_backend(self):
        with patch('src.memory.utils.storage_backends.get_database_manager') as mock_db_manager:
            mock_manager = AsyncMock()
            mock_manager.mongodb = AsyncMock()
            mock_manager.mongodb.database = AsyncMock()
            mock_db_manager.return_value = mock_manager
            return MongoDBStorageBackend()
    
    @pytest.mark.asyncio
    async def test_initialize(self, mongodb_backend):
        """Test MongoDB backend initialization."""
        mongodb_backend.db_manager.initialize_all = AsyncMock()
        mongodb_backend._create_indexes = AsyncMock()
        
        await mongodb_backend.initialize()
        
        mongodb_backend.db_manager.initialize_all.assert_called_once()
        mongodb_backend._create_indexes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_conversation(self, mongodb_backend):
        """Test storing conversation."""
        conversation = Conversation(
            id="conv_1",
            user_id="test_user",
            messages=[
                Message(
                    id="msg_1",
                    role="user",
                    content="Hello",
                    timestamp=datetime.now(timezone.utc)
                )
            ],
            timestamp=datetime.now(timezone.utc)
        )
        
        mock_collection = AsyncMock()
        mongodb_backend.db_manager.mongodb.database.conversations = mock_collection
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock()
        
        await mongodb_backend.store_conversation(conversation)
        
        mongodb_backend.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_found(self, mongodb_backend):
        """Test getting conversation when it exists."""
        mock_doc = {
            "id": "conv_1",
            "user_id": "test_user",
            "messages": [
                {
                    "id": "msg_1",
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_doc)
        
        result = await mongodb_backend.get_conversation("conv_1")
        
        assert result is not None
        assert result.id == "conv_1"
        assert result.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, mongodb_backend):
        """Test getting conversation when it doesn't exist."""
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=None)
        
        result = await mongodb_backend.get_conversation("conv_1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_conversations(self, mongodb_backend):
        """Test getting user conversations."""
        mock_docs = [
            {
                "id": "conv_1",
                "user_id": "test_user",
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_docs)
        
        result = await mongodb_backend.get_user_conversations("test_user")
        
        assert len(result) == 1
        assert result[0].id == "conv_1"
        assert result[0].user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, mongodb_backend):
        """Test deleting conversation."""
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=1)
        
        await mongodb_backend.delete_conversation("conv_1")
        
        mongodb_backend.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_all_user_data(self, mongodb_backend):
        """Test deleting all user data."""
        mongodb_backend.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=5)
        
        await mongodb_backend.delete_all_user_data("test_user")
        
        mongodb_backend.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, mongodb_backend):
        """Test health check."""
        mongodb_backend.db_manager.mongodb.health_check = AsyncMock(return_value=True)
        
        result = await mongodb_backend.health_check()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_preferences_methods_not_implemented(self, mongodb_backend):
        """Test that preferences methods raise NotImplementedError."""
        preferences = UserPreferences(
            user_id="test_user"
        )
        
        with pytest.raises(NotImplementedError):
            await mongodb_backend.store_user_preferences(preferences)
        
        with pytest.raises(NotImplementedError):
            await mongodb_backend.get_user_preferences("test_user")


class TestHybridStorageBackend:
    """Tests for hybrid storage backend."""
    
    @pytest.fixture
    def hybrid_backend(self):
        with patch('src.memory.utils.storage_backends.PostgreSQLStorageBackend') as mock_pg, \
             patch('src.memory.utils.storage_backends.MongoDBStorageBackend') as mock_mongo:
            
            mock_pg_instance = AsyncMock()
            mock_mongo_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_mongo.return_value = mock_mongo_instance
            
            backend = HybridStorageBackend()
            backend.postgres_backend = mock_pg_instance
            backend.mongodb_backend = mock_mongo_instance
            return backend
    
    @pytest.mark.asyncio
    async def test_initialize(self, hybrid_backend):
        """Test hybrid backend initialization."""
        await hybrid_backend.initialize()
        
        hybrid_backend.postgres_backend.initialize.assert_called_once()
        hybrid_backend.mongodb_backend.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, hybrid_backend):
        """Test hybrid backend close."""
        await hybrid_backend.close()
        
        hybrid_backend.postgres_backend.close.assert_called_once()
        hybrid_backend.mongodb_backend.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conversation_operations_use_mongodb(self, hybrid_backend):
        """Test that conversation operations use MongoDB backend."""
        conversation = Conversation(
            id="conv_1",
            user_id="test_user",
            messages=[],
            timestamp=datetime.now(timezone.utc)
        )
        
        # Test store_conversation
        await hybrid_backend.store_conversation(conversation)
        hybrid_backend.mongodb_backend.store_conversation.assert_called_once_with(conversation)
        
        # Test get_conversation
        await hybrid_backend.get_conversation("conv_1")
        hybrid_backend.mongodb_backend.get_conversation.assert_called_once_with("conv_1")
        
        # Test get_user_conversations
        await hybrid_backend.get_user_conversations("test_user")
        hybrid_backend.mongodb_backend.get_user_conversations.assert_called_once_with("test_user", None, None, None)
        
        # Test delete_conversation
        await hybrid_backend.delete_conversation("conv_1")
        hybrid_backend.mongodb_backend.delete_conversation.assert_called_once_with("conv_1")
    
    @pytest.mark.asyncio
    async def test_preferences_operations_use_postgres(self, hybrid_backend):
        """Test that preferences operations use PostgreSQL backend."""
        preferences = UserPreferences(
            user_id="test_user"
        )
        
        # Test store_user_preferences
        await hybrid_backend.store_user_preferences(preferences)
        hybrid_backend.postgres_backend.store_user_preferences.assert_called_once_with(preferences)
        
        # Test get_user_preferences
        await hybrid_backend.get_user_preferences("test_user")
        hybrid_backend.postgres_backend.get_user_preferences.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_delete_all_user_data_uses_both_backends(self, hybrid_backend):
        """Test that delete_all_user_data uses both backends."""
        await hybrid_backend.delete_all_user_data("test_user")
        
        hybrid_backend.postgres_backend.delete_all_user_data.assert_called_once_with("test_user")
        hybrid_backend.mongodb_backend.delete_all_user_data.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_health_check_requires_both_backends(self, hybrid_backend):
        """Test that health check requires both backends to be healthy."""
        # Both healthy
        hybrid_backend.postgres_backend.health_check.return_value = True
        hybrid_backend.mongodb_backend.health_check.return_value = True
        result = await hybrid_backend.health_check()
        assert result is True
        
        # One unhealthy
        hybrid_backend.postgres_backend.health_check.return_value = False
        hybrid_backend.mongodb_backend.health_check.return_value = True
        result = await hybrid_backend.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_data_summary_combines_both_backends(self, hybrid_backend):
        """Test that get_user_data_summary combines data from both backends."""
        postgres_summary = {"preferences_count": 1, "privacy_settings_count": 1}
        mongodb_summary = {"conversation_count": 5}
        
        hybrid_backend.postgres_backend.get_user_data_summary.return_value = postgres_summary
        hybrid_backend.mongodb_backend.get_user_data_summary.return_value = mongodb_summary
        
        result = await hybrid_backend.get_user_data_summary("test_user")
        
        assert result == {
            "postgres": postgres_summary,
            "mongodb": mongodb_summary
        }