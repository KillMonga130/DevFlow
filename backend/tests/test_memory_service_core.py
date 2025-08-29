"""
Tests for the main memory service core functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.memory.services.memory_service import MemoryService
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    SearchQuery, SearchResult, DeleteOptions, UserDataExport,
    PrivacySettings, MessageExchange
)
from src.memory.models.privacy import DeleteScope


class TestMemoryServiceCore:
    """Test cases for the main memory service core functionality."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage layer."""
        storage = AsyncMock()
        storage.initialize = AsyncMock()
        storage.health_check = AsyncMock()
        storage.store_conversation = AsyncMock()
        storage.get_privacy_settings = AsyncMock()
        storage.store_privacy_settings = AsyncMock()
        return storage
    
    @pytest.fixture
    def mock_context_manager(self):
        """Mock context manager."""
        context_manager = AsyncMock()
        context_manager.build_context = AsyncMock()
        context_manager.update_context = AsyncMock()
        return context_manager
    
    @pytest.fixture
    def mock_preference_engine(self):
        """Mock preference engine."""
        preference_engine = AsyncMock()
        preference_engine.get_preferences = AsyncMock()
        preference_engine.analyze_user_preferences = AsyncMock()
        return preference_engine
    
    @pytest.fixture
    def mock_search_service(self):
        """Mock search service."""
        search_service = AsyncMock()
        search_service.search_conversations = AsyncMock()
        search_service.index_conversation = AsyncMock()
        return search_service
    
    @pytest.fixture
    def mock_privacy_controller(self):
        """Mock privacy controller."""
        privacy_controller = AsyncMock()
        privacy_controller.initialize = AsyncMock()
        privacy_controller.audit_data_access = AsyncMock()
        privacy_controller.delete_user_data = AsyncMock()
        privacy_controller.export_user_data = AsyncMock()
        privacy_controller.apply_retention_policy = AsyncMock()
        return privacy_controller
    
    @pytest.fixture
    def memory_service(self, mock_storage, mock_context_manager, mock_preference_engine, 
                      mock_search_service, mock_privacy_controller):
        """Create memory service with mocked dependencies."""
        return MemoryService(
            context_manager=mock_context_manager,
            preference_engine=mock_preference_engine,
            search_service=mock_search_service,
            privacy_controller=mock_privacy_controller,
            storage_layer=mock_storage
        )
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        return Conversation(
            id="conv_123",
            user_id="user_456",
            timestamp=datetime.now(timezone.utc),
            messages=[
                Message(
                    id="msg_1",
                    role=MessageRole.USER,
                    content="Hello, how are you?",
                    timestamp=datetime.now(timezone.utc)
                ),
                Message(
                    id="msg_2",
                    role=MessageRole.ASSISTANT,
                    content="I'm doing well, thank you for asking!",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, memory_service, mock_storage, mock_privacy_controller):
        """Test memory service initialization."""
        await memory_service.initialize()
        
        mock_storage.initialize.assert_called_once()
        mock_privacy_controller.initialize.assert_called_once()
        assert memory_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialization_idempotent(self, memory_service, mock_storage):
        """Test that initialization is idempotent."""
        await memory_service.initialize()
        await memory_service.initialize()  # Second call should not reinitialize
        
        mock_storage.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_conversation_success(self, memory_service, mock_storage, 
                                            mock_search_service, mock_context_manager,
                                            mock_preference_engine, mock_privacy_controller,
                                            sample_conversation):
        """Test successful conversation storage."""
        await memory_service.initialize()
        
        await memory_service.store_conversation("user_456", sample_conversation)
        
        # Verify storage was called
        mock_storage.store_conversation.assert_called_once_with(sample_conversation)
        
        # Verify search indexing
        mock_search_service.index_conversation.assert_called_once()
        
        # Verify context update
        mock_context_manager.update_context.assert_called_once()
        
        # Verify audit logging
        mock_privacy_controller.audit_data_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_conversation_with_fallback(self, memory_service, mock_storage,
                                                  mock_search_service, sample_conversation):
        """Test conversation storage with fallback when components fail."""
        await memory_service.initialize()
        
        # Make search service fail
        mock_search_service.index_conversation.side_effect = Exception("Search indexing failed")
        
        # Storage should still succeed
        await memory_service.store_conversation("user_456", sample_conversation)
        
        # Verify storage was still called
        mock_storage.store_conversation.assert_called_with(sample_conversation)
    
    @pytest.mark.asyncio
    async def test_store_conversation_complete_failure(self, memory_service, mock_storage,
                                                     sample_conversation):
        """Test conversation storage when even fallback fails."""
        await memory_service.initialize()
        
        # Make storage fail completely
        mock_storage.store_conversation.side_effect = Exception("Storage failed")
        
        with pytest.raises(Exception):
            await memory_service.store_conversation("user_456", sample_conversation)
    
    @pytest.mark.asyncio
    async def test_retrieve_context_success(self, memory_service, mock_context_manager,
                                          mock_preference_engine, mock_privacy_controller):
        """Test successful context retrieval."""
        await memory_service.initialize()
        
        # Setup mocks
        expected_context = ConversationContext(user_id="user_456")
        mock_context_manager.build_context.return_value = expected_context
        
        result = await memory_service.retrieve_context("user_456")
        
        assert result == expected_context
        mock_context_manager.build_context.assert_called_once_with("user_456", "")
        mock_privacy_controller.audit_data_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_context_with_fallback(self, memory_service, mock_context_manager):
        """Test context retrieval with fallback when context manager fails."""
        await memory_service.initialize()
        
        # Make context manager fail
        mock_context_manager.build_context.side_effect = Exception("Context build failed")
        
        result = await memory_service.retrieve_context("user_456")
        
        # Should return basic context
        assert result.user_id == "user_456"
    
    @pytest.mark.asyncio
    async def test_search_history_success(self, memory_service, mock_search_service,
                                        mock_privacy_controller, mock_storage):
        """Test successful history search."""
        await memory_service.initialize()
        
        # Setup mocks
        query = SearchQuery(user_id="user_456", keywords=["test"])
        expected_results = [SearchResult(
            conversation_id="conv_123", 
            relevance_score=0.8,
            timestamp=datetime.now(timezone.utc),
            content_snippet="Test content"
        )]
        mock_search_service.search_conversations.return_value = expected_results
        mock_storage.get_privacy_settings.return_value = PrivacySettings(user_id="user_456")
        
        result = await memory_service.search_history("user_456", query)
        
        assert result == expected_results
        mock_search_service.search_conversations.assert_called_once_with(query)
        # Should be called twice: once for privacy settings, once for search
        assert mock_privacy_controller.audit_data_access.call_count == 2
    
    @pytest.mark.asyncio
    async def test_search_history_privacy_disabled(self, memory_service, mock_storage):
        """Test search when disabled by privacy settings."""
        await memory_service.initialize()
        
        # Setup privacy settings that disable search indexing
        privacy_settings = PrivacySettings(user_id="user_456", allow_search_indexing=False)
        mock_storage.get_privacy_settings.return_value = privacy_settings
        
        query = SearchQuery(user_id="user_456", keywords=["test"])
        result = await memory_service.search_history("user_456", query)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_search_history_with_error(self, memory_service, mock_search_service):
        """Test search history when search service fails."""
        await memory_service.initialize()
        
        # Make search service fail
        mock_search_service.search_conversations.side_effect = Exception("Search failed")
        
        query = SearchQuery(user_id="user_456", keywords=["test"])
        result = await memory_service.search_history("user_456", query)
        
        # Should return empty results on failure
        assert result == []
    
    @pytest.mark.asyncio
    async def test_delete_user_data(self, memory_service, mock_privacy_controller):
        """Test user data deletion."""
        await memory_service.initialize()
        
        options = DeleteOptions(
            scope=DeleteScope.ALL_DATA,
            confirm_deletion=True,
            reason="User request"
        )
        
        await memory_service.delete_user_data("user_456", options)
        
        mock_privacy_controller.delete_user_data.assert_called_once_with("user_456", options)
    
    @pytest.mark.asyncio
    async def test_delete_user_data_default_options(self, memory_service, mock_privacy_controller):
        """Test user data deletion with default options."""
        await memory_service.initialize()
        
        await memory_service.delete_user_data("user_456")
        
        # Should be called with default options
        mock_privacy_controller.delete_user_data.assert_called_once()
        call_args = mock_privacy_controller.delete_user_data.call_args
        assert call_args[0][0] == "user_456"  # user_id
        assert call_args[0][1].scope == DeleteScope.ALL_DATA
        assert call_args[0][1].confirm_deletion is True
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, memory_service, mock_privacy_controller):
        """Test user data export."""
        await memory_service.initialize()
        
        expected_export = UserDataExport(user_id="user_456")
        mock_privacy_controller.export_user_data.return_value = expected_export
        
        result = await memory_service.export_user_data("user_456")
        
        assert result == expected_export
        mock_privacy_controller.export_user_data.assert_called_once_with("user_456")
    
    @pytest.mark.asyncio
    async def test_update_privacy_settings(self, memory_service, mock_storage,
                                         mock_privacy_controller):
        """Test privacy settings update."""
        await memory_service.initialize()
        
        settings = PrivacySettings(user_id="user_456")
        
        await memory_service.update_privacy_settings("user_456", settings)
        
        mock_storage.store_privacy_settings.assert_called_once_with(settings)
        mock_privacy_controller.audit_data_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_privacy_settings(self, memory_service, mock_storage,
                                      mock_privacy_controller):
        """Test privacy settings retrieval."""
        await memory_service.initialize()
        
        expected_settings = PrivacySettings(user_id="user_456")
        mock_storage.get_privacy_settings.return_value = expected_settings
        
        result = await memory_service.get_privacy_settings("user_456")
        
        assert result == expected_settings
        mock_storage.get_privacy_settings.assert_called_once_with("user_456")
        mock_privacy_controller.audit_data_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_privacy_settings_fallback(self, memory_service, mock_storage):
        """Test privacy settings retrieval with fallback."""
        await memory_service.initialize()
        
        # Make storage fail
        mock_storage.get_privacy_settings.side_effect = Exception("Storage failed")
        
        result = await memory_service.get_privacy_settings("user_456")
        
        # Should return default settings
        assert result.user_id == "user_456"
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, memory_service, mock_storage):
        """Test health check when all components are healthy."""
        await memory_service.initialize()
        
        mock_storage.health_check.return_value = True
        
        result = await memory_service.health_check()
        
        assert result["memory_service"] == "healthy"
        assert result["initialized"] is True
        assert result["components"]["storage"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_storage_unhealthy(self, memory_service, mock_storage):
        """Test health check when storage is unhealthy."""
        await memory_service.initialize()
        
        mock_storage.health_check.side_effect = Exception("Storage connection failed")
        
        result = await memory_service.health_check()
        
        assert result["memory_service"] == "healthy"
        assert "unhealthy: Storage connection failed" in result["components"]["storage"]
    
    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, memory_service):
        """Test health check when service is not initialized."""
        result = await memory_service.health_check()
        
        assert result["initialized"] is False
    
    @pytest.mark.asyncio
    async def test_auto_initialization(self, memory_service, mock_storage, sample_conversation):
        """Test that operations auto-initialize the service."""
        # Service not manually initialized
        assert not memory_service._initialized
        
        # Calling an operation should auto-initialize
        await memory_service.store_conversation("user_456", sample_conversation)
        
        # Should be initialized now
        assert memory_service._initialized
        mock_storage.initialize.assert_called_once()


class TestMemoryServiceIntegration:
    """Integration tests for memory service with real-like scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self):
        """Test a complete conversation workflow from storage to retrieval."""
        # This would be an integration test with real components
        # For now, we'll use mocks but test the full flow
        
        storage = AsyncMock()
        context_manager = AsyncMock()
        preference_engine = AsyncMock()
        search_service = AsyncMock()
        privacy_controller = AsyncMock()
        
        # Setup initialization
        storage.initialize = AsyncMock()
        privacy_controller.initialize = AsyncMock()
        
        memory_service = MemoryService(
            context_manager=context_manager,
            preference_engine=preference_engine,
            search_service=search_service,
            privacy_controller=privacy_controller,
            storage_layer=storage
        )
        
        # Create conversation
        conversation = Conversation(
            id="conv_123",
            user_id="user_456",
            timestamp=datetime.now(timezone.utc),
            messages=[
                Message(
                    id="msg_1",
                    role=MessageRole.USER,
                    content="What's the weather like?",
                    timestamp=datetime.now(timezone.utc)
                ),
                Message(
                    id="msg_2",
                    role=MessageRole.ASSISTANT,
                    content="I don't have access to current weather data.",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        )
        
        # Store conversation
        await memory_service.store_conversation("user_456", conversation)
        
        # Verify all components were called
        storage.store_conversation.assert_called_once()
        search_service.index_conversation.assert_called_once()
        context_manager.update_context.assert_called_once()
        privacy_controller.audit_data_access.assert_called()
        
        # Retrieve context
        expected_context = ConversationContext(user_id="user_456")
        context_manager.build_context.return_value = expected_context
        
        context = await memory_service.retrieve_context("user_456")
        
        assert context.user_id == "user_456"
        context_manager.build_context.assert_called_once()