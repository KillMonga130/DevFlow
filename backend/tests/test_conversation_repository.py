"""
Integration tests for conversation repository.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.memory.repositories.conversation_repository import (
    ConversationRepository, get_conversation_repository
)
from src.memory.models import Conversation, Message, MessageRole


class TestConversationRepository:
    """Tests for conversation repository."""
    
    @pytest.fixture
    def conversation_repo(self):
        with patch('src.memory.repositories.conversation_repository.get_database_manager') as mock_db_manager:
            mock_manager = AsyncMock()
            mock_manager.mongodb = AsyncMock()
            mock_manager.mongodb.database = AsyncMock()
            mock_db_manager.return_value = mock_manager
            return ConversationRepository()
    
    @pytest.fixture
    def sample_conversation(self):
        return Conversation(
            id="conv_1",
            user_id="test_user",
            messages=[
                Message(
                    id="msg_1",
                    role=MessageRole.USER,
                    content="Hello",
                    timestamp=datetime.now(timezone.utc)
                ),
                Message(
                    id="msg_2",
                    role=MessageRole.ASSISTANT,
                    content="Hi there!",
                    timestamp=datetime.now(timezone.utc)
                )
            ],
            timestamp=datetime.now(timezone.utc),
            tags=["greeting", "test"]
        )
    
    @pytest.mark.asyncio
    async def test_initialize(self, conversation_repo):
        """Test repository initialization."""
        conversation_repo.db_manager.initialize_all = AsyncMock()
        conversation_repo._create_indexes = AsyncMock()
        
        await conversation_repo.initialize()
        
        assert conversation_repo._initialized is True
        conversation_repo.db_manager.initialize_all.assert_called_once()
        conversation_repo._create_indexes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_conversation(self, conversation_repo, sample_conversation):
        """Test storing a conversation."""
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.upserted_id = "new_id"
        mock_result.matched_count = 0
        mock_collection.replace_one.return_value = mock_result
        
        conversation_repo.db_manager.mongodb.database.conversations = mock_collection
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value="new_id")
        conversation_repo._initialized = True
        
        await conversation_repo.store_conversation(sample_conversation)
        
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_found(self, conversation_repo):
        """Test getting a conversation that exists."""
        mock_doc = {
            "id": "conv_1",
            "user_id": "test_user",
            "messages": [
                {
                    "id": "msg_1",
                    "role": "user",
                    "content": "Hello",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {}
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tags": ["test"],
            "metadata": {"total_messages": 1}
        }
        
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_doc)
        conversation_repo._initialized = True
        
        result = await conversation_repo.get_conversation("conv_1")
        
        assert result is not None
        assert result.id == "conv_1"
        assert result.user_id == "test_user"
        assert len(result.messages) == 1
    
    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, conversation_repo):
        """Test getting a conversation that doesn't exist."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=None)
        conversation_repo._initialized = True
        
        result = await conversation_repo.get_conversation("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_conversations(self, conversation_repo):
        """Test getting conversations for a user."""
        mock_docs = [
            {
                "id": "conv_1",
                "user_id": "test_user",
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tags": [],
                "metadata": {"total_messages": 0}
            },
            {
                "id": "conv_2",
                "user_id": "test_user",
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tags": [],
                "metadata": {"total_messages": 0}
            }
        ]
        
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_docs)
        conversation_repo._initialized = True
        
        result = await conversation_repo.get_user_conversations("test_user")
        
        assert len(result) == 2
        assert all(conv.user_id == "test_user" for conv in result)
    
    @pytest.mark.asyncio
    async def test_get_user_conversations_with_filters(self, conversation_repo):
        """Test getting conversations with date and tag filters."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=[])
        conversation_repo._initialized = True
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        tags = ["important"]
        
        await conversation_repo.get_user_conversations(
            "test_user", 
            limit=10,
            start_date=start_date,
            end_date=end_date,
            tags=tags
        )
        
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_conversations(self, conversation_repo):
        """Test searching conversations by text."""
        mock_docs = [
            {
                "id": "conv_1",
                "user_id": "test_user",
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "content": "Hello world",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {}
                    }
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tags": [],
                "metadata": {"total_messages": 1}
            }
        ]
        
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_docs)
        conversation_repo._initialized = True
        
        result = await conversation_repo.search_conversations("test_user", "hello")
        
        assert len(result) == 1
        assert result[0].id == "conv_1"
    
    @pytest.mark.asyncio
    async def test_get_recent_conversations(self, conversation_repo):
        """Test getting recent conversations."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=[])
        conversation_repo._initialized = True
        
        await conversation_repo.get_recent_conversations("test_user", days=7, limit=20)
        
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_conversation_summary(self, conversation_repo):
        """Test updating conversation summary."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=True)
        conversation_repo._initialized = True
        
        result = await conversation_repo.update_conversation_summary("conv_1", "New summary")
        
        assert result is True
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_tags_to_conversation(self, conversation_repo):
        """Test adding tags to a conversation."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=True)
        conversation_repo._initialized = True
        
        result = await conversation_repo.add_tags_to_conversation("conv_1", ["new_tag", "another_tag"])
        
        assert result is True
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_tags_from_conversation(self, conversation_repo):
        """Test removing tags from a conversation."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=True)
        conversation_repo._initialized = True
        
        result = await conversation_repo.remove_tags_from_conversation("conv_1", ["old_tag"])
        
        assert result is True
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_repo):
        """Test deleting a conversation."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=True)
        conversation_repo._initialized = True
        
        result = await conversation_repo.delete_conversation("conv_1")
        
        assert result is True
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_conversations(self, conversation_repo):
        """Test deleting user conversations."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=5)
        conversation_repo._initialized = True
        
        result = await conversation_repo.delete_user_conversations("test_user")
        
        assert result == 5
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_conversations_with_age_filter(self, conversation_repo):
        """Test deleting old user conversations."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=3)
        conversation_repo._initialized = True
        
        result = await conversation_repo.delete_user_conversations("test_user", older_than_days=30)
        
        assert result == 3
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_statistics(self, conversation_repo):
        """Test getting conversation statistics."""
        mock_stats = {
            "total_conversations": 10,
            "total_messages": 50,
            "earliest_conversation": datetime.now(timezone.utc) - timedelta(days=30),
            "latest_conversation": datetime.now(timezone.utc),
            "avg_messages_per_conversation": 5.0
        }
        
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=mock_stats)
        conversation_repo._get_tag_statistics = AsyncMock(return_value={"test": 5, "important": 3})
        conversation_repo._initialized = True
        
        result = await conversation_repo.get_conversation_statistics("test_user")
        
        assert result["total_conversations"] == 10
        assert result["total_messages"] == 50
        assert "conversation_span_days" in result
        assert "tag_statistics" in result
    
    @pytest.mark.asyncio
    async def test_get_conversation_count(self, conversation_repo):
        """Test getting conversation count."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=15)
        conversation_repo._initialized = True
        
        result = await conversation_repo.get_conversation_count("test_user")
        
        assert result == 15
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_conversation_count_with_date_range(self, conversation_repo):
        """Test getting conversation count with date range."""
        conversation_repo.db_manager.mongodb.execute_with_retry = AsyncMock(return_value=8)
        conversation_repo._initialized = True
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        result = await conversation_repo.get_conversation_count(
            "test_user", 
            start_date=start_date, 
            end_date=end_date
        )
        
        assert result == 8
        conversation_repo.db_manager.mongodb.execute_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, conversation_repo):
        """Test successful health check."""
        conversation_repo.db_manager.mongodb.health_check = AsyncMock(return_value=True)
        conversation_repo._initialized = True
        
        result = await conversation_repo.health_check()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, conversation_repo):
        """Test health check failure."""
        conversation_repo.db_manager.mongodb.health_check = AsyncMock(side_effect=Exception("DB error"))
        
        result = await conversation_repo.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close(self, conversation_repo):
        """Test closing the repository."""
        conversation_repo._initialized = True
        conversation_repo.db_manager.close_all = AsyncMock()
        
        await conversation_repo.close()
        
        assert conversation_repo._initialized is False
        conversation_repo.db_manager.close_all.assert_called_once()


def test_get_conversation_repository():
    """Test getting the global repository instance."""
    repo1 = get_conversation_repository()
    repo2 = get_conversation_repository()
    
    assert repo1 is repo2  # Should return the same instance