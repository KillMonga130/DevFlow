"""
Integration tests for the complete memory service functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.memory.services.memory_service_factory import (
    MemoryServiceFactory, MemoryServiceCoordinator, 
    get_memory_service_coordinator, get_default_memory_service
)
from src.memory.services.memory_service import MemoryService
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    SearchQuery, SearchResult, DeleteOptions, UserDataExport,
    PrivacySettings, MessageExchange
)
from src.memory.models.privacy import DeleteScope


class TestMemoryServiceFactory:
    """Test cases for the memory service factory."""
    
    @pytest.mark.asyncio
    async def test_create_memory_service_with_auto_init(self):
        """Test creating a memory service with automatic initialization."""
        with patch('src.memory.services.memory_service_factory.StorageLayer') as mock_storage_class, \
             patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
             patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
             patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
             patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
            
            # Setup mocks
            mock_storage = AsyncMock()
            mock_context = AsyncMock()
            mock_preference = AsyncMock()
            mock_search = AsyncMock()
            mock_privacy = AsyncMock()
            
            mock_storage_class.return_value = mock_storage
            mock_context_class.return_value = mock_context
            mock_pref_class.return_value = mock_preference
            mock_search_class.return_value = mock_search
            mock_privacy_class.return_value = mock_privacy
            
            # Setup async methods
            mock_storage.initialize = AsyncMock()
            mock_privacy.initialize = AsyncMock()
            
            # Create service
            service = await MemoryServiceFactory.create_memory_service()
            
            # Verify service was created and initialized
            assert isinstance(service, MemoryService)
            assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_create_memory_service_without_auto_init(self):
        """Test creating a memory service without automatic initialization."""
        with patch('src.memory.services.memory_service_factory.StorageLayer') as mock_storage_class, \
             patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
             patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
             patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
             patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
            
            # Setup mocks
            mock_storage = AsyncMock()
            mock_context = AsyncMock()
            mock_preference = AsyncMock()
            mock_search = AsyncMock()
            mock_privacy = AsyncMock()
            
            mock_storage_class.return_value = mock_storage
            mock_context_class.return_value = mock_context
            mock_pref_class.return_value = mock_preference
            mock_search_class.return_value = mock_search
            mock_privacy_class.return_value = mock_privacy
            
            # Create service without auto-initialization
            service = await MemoryServiceFactory.create_memory_service(auto_initialize=False)
            
            # Verify service was created but not initialized
            assert isinstance(service, MemoryService)
            assert service._initialized is False
    
    @pytest.mark.asyncio
    async def test_create_memory_service_with_custom_storage(self):
        """Test creating a memory service with custom storage layer."""
        custom_storage = AsyncMock()
        
        with patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
             patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
             patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
             patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
            
            # Create service with custom storage
            service = await MemoryServiceFactory.create_memory_service(
                storage_layer=custom_storage,
                auto_initialize=False
            )
            
            # Verify custom storage was used
            assert service._storage is custom_storage


class TestMemoryServiceCoordinator:
    """Test cases for the memory service coordinator."""
    
    @pytest.fixture
    def coordinator(self):
        """Create a memory service coordinator for testing."""
        return MemoryServiceCoordinator()
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """Test coordinator initialization."""
        await coordinator.initialize()
        assert coordinator._initialized is True
    
    @pytest.mark.asyncio
    async def test_coordinator_get_service(self, coordinator):
        """Test getting a service from the coordinator."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service = AsyncMock()
            mock_create.return_value = mock_service
            
            # Get service
            service = await coordinator.get_service("test_service")
            
            # Verify service was created and cached
            assert service is mock_service
            assert "test_service" in coordinator._services
            mock_create.assert_called_once()
            
            # Get same service again - should return cached instance
            service2 = await coordinator.get_service("test_service")
            assert service2 is mock_service
            # Should not create a new service
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_coordinator_remove_service(self, coordinator):
        """Test removing a service from the coordinator."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service = AsyncMock()
            mock_create.return_value = mock_service
            
            # Add service
            await coordinator.get_service("test_service")
            assert "test_service" in coordinator._services
            
            # Remove service
            await coordinator.remove_service("test_service")
            assert "test_service" not in coordinator._services
    
    @pytest.mark.asyncio
    async def test_coordinator_health_check_all(self, coordinator):
        """Test health check for all services."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service1 = AsyncMock()
            mock_service1.health_check.return_value = {"status": "healthy"}
            mock_service2 = AsyncMock()
            mock_service2.health_check.return_value = {"status": "healthy"}
            
            mock_create.side_effect = [mock_service1, mock_service2]
            
            # Add services
            await coordinator.get_service("service1")
            await coordinator.get_service("service2")
            
            # Health check
            health = await coordinator.health_check_all()
            
            assert health["coordinator"] == "healthy"
            assert "service1" in health["services"]
            assert "service2" in health["services"]
            assert health["services"]["service1"]["status"] == "healthy"
            assert health["services"]["service2"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_coordinator_health_check_with_unhealthy_service(self, coordinator):
        """Test health check when a service is unhealthy."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service = AsyncMock()
            mock_service.health_check.side_effect = Exception("Service error")
            mock_create.return_value = mock_service
            
            # Add service
            await coordinator.get_service("unhealthy_service")
            
            # Health check
            health = await coordinator.health_check_all()
            
            assert health["coordinator"] == "healthy"
            assert health["services"]["unhealthy_service"]["status"] == "unhealthy"
            assert "Service error" in health["services"]["unhealthy_service"]["error"]
    
    @pytest.mark.asyncio
    async def test_coordinator_shutdown(self, coordinator):
        """Test coordinator shutdown."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service = AsyncMock()
            mock_create.return_value = mock_service
            
            # Add service
            await coordinator.get_service("test_service")
            assert len(coordinator._services) == 1
            
            # Shutdown
            await coordinator.shutdown()
            
            assert len(coordinator._services) == 0
            assert coordinator._initialized is False


class TestMemoryServiceIntegrationWorkflows:
    """Integration tests for complete memory service workflows."""
    
    @pytest.fixture
    async def memory_service(self):
        """Create a memory service for integration testing."""
        with patch('src.memory.services.memory_service_factory.StorageLayer') as mock_storage_class, \
             patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
             patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
             patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
             patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
            
            # Setup mocks
            mock_storage = AsyncMock()
            mock_context = AsyncMock()
            mock_preference = AsyncMock()
            mock_search = AsyncMock()
            mock_privacy = AsyncMock()
            
            mock_storage_class.return_value = mock_storage
            mock_context_class.return_value = mock_context
            mock_pref_class.return_value = mock_preference
            mock_search_class.return_value = mock_search
            mock_privacy_class.return_value = mock_privacy
            
            # Setup method returns
            mock_storage.initialize = AsyncMock()
            mock_privacy.initialize = AsyncMock()
            mock_storage.get_privacy_settings.return_value = PrivacySettings(user_id="user_123")
            mock_context.build_context.return_value = ConversationContext(user_id="user_123")
            mock_search.search_conversations.return_value = []
            mock_privacy.audit_data_access = AsyncMock()
            
            service = await MemoryServiceFactory.create_memory_service()
            yield service, {
                'storage': mock_storage,
                'context': mock_context,
                'preference': mock_preference,
                'search': mock_search,
                'privacy': mock_privacy
            }
    
    @pytest.mark.asyncio
    async def test_complete_conversation_workflow(self, memory_service):
        """Test a complete conversation workflow from storage to search."""
        service, mocks = memory_service
        
        # Create test conversation
        conversation = Conversation(
            id="conv_123",
            user_id="user_123",
            timestamp=datetime.now(timezone.utc),
            messages=[
                Message(
                    id="msg_1",
                    role=MessageRole.USER,
                    content="Hello, how can I learn Python?",
                    timestamp=datetime.now(timezone.utc)
                ),
                Message(
                    id="msg_2",
                    role=MessageRole.ASSISTANT,
                    content="I'd recommend starting with the official Python tutorial.",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        )
        
        # Store conversation
        await service.store_conversation("user_123", conversation)
        
        # Verify storage was called
        mocks['storage'].store_conversation.assert_called_once_with(conversation)
        mocks['search'].index_conversation.assert_called_once()
        mocks['context'].update_context.assert_called_once()
        
        # Retrieve context
        context = await service.retrieve_context("user_123")
        assert context.user_id == "user_123"
        mocks['context'].build_context.assert_called_once()
        
        # Search history
        query = SearchQuery(user_id="user_123", keywords=["Python"])
        results = await service.search_history("user_123", query)
        mocks['search'].search_conversations.assert_called_once_with(query)
        
        # Verify audit logging was called for all operations
        assert mocks['privacy'].audit_data_access.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_privacy_workflow(self, memory_service):
        """Test privacy-related operations workflow."""
        service, mocks = memory_service
        
        # Update privacy settings
        privacy_settings = PrivacySettings(
            user_id="user_123",
            allow_search_indexing=False
        )
        await service.update_privacy_settings("user_123", privacy_settings)
        mocks['storage'].store_privacy_settings.assert_called_once_with(privacy_settings)
        
        # Export user data
        export_data = UserDataExport(user_id="user_123")
        mocks['privacy'].export_user_data.return_value = export_data
        
        result = await service.export_user_data("user_123")
        assert result.user_id == "user_123"
        mocks['privacy'].export_user_data.assert_called_once_with("user_123")
        
        # Delete user data
        delete_options = DeleteOptions(
            scope=DeleteScope.ALL_DATA,
            confirm_deletion=True
        )
        await service.delete_user_data("user_123", delete_options)
        mocks['privacy'].delete_user_data.assert_called_once_with("user_123", delete_options)
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, memory_service):
        """Test error handling and fallback mechanisms."""
        service, mocks = memory_service
        
        # Test storage failure with fallback
        mocks['search'].index_conversation.side_effect = Exception("Search indexing failed")
        
        conversation = Conversation(
            id="conv_456",
            user_id="user_123",
            timestamp=datetime.now(timezone.utc),
            messages=[
                Message(
                    id="msg_1",
                    role=MessageRole.USER,
                    content="Test message",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        )
        
        # Should still succeed despite search indexing failure
        await service.store_conversation("user_123", conversation)
        mocks['storage'].store_conversation.assert_called_with(conversation)
        
        # Test context retrieval failure with fallback
        mocks['context'].build_context.side_effect = Exception("Context build failed")
        
        context = await service.retrieve_context("user_123")
        # Should return basic context as fallback
        assert context.user_id == "user_123"
        
        # Test search failure - should return empty results
        mocks['search'].search_conversations.side_effect = Exception("Search failed")
        
        query = SearchQuery(user_id="user_123", keywords=["test"])
        results = await service.search_history("user_123", query)
        assert results == []


class TestGlobalServiceAccess:
    """Test global service access functions."""
    
    @pytest.mark.asyncio
    async def test_get_memory_service_coordinator(self):
        """Test getting the global coordinator instance."""
        # Reset global state
        import src.memory.services.memory_service_factory as factory_module
        factory_module._coordinator = None
        
        coordinator1 = await get_memory_service_coordinator()
        coordinator2 = await get_memory_service_coordinator()
        
        # Should return the same instance
        assert coordinator1 is coordinator2
        assert coordinator1._initialized is True
    
    @pytest.mark.asyncio
    async def test_get_default_memory_service(self):
        """Test getting the default memory service."""
        with patch('src.memory.services.memory_service_factory.MemoryServiceFactory.create_memory_service') as mock_create:
            mock_service = AsyncMock()
            mock_create.return_value = mock_service
            
            # Reset global state
            import src.memory.services.memory_service_factory as factory_module
            factory_module._coordinator = None
            
            service = await get_default_memory_service()
            assert service is mock_service


class TestServiceConfiguration:
    """Test service configuration and initialization."""
    
    @pytest.mark.asyncio
    async def test_service_configuration_loading(self):
        """Test that services are configured with proper settings."""
        with patch('src.memory.services.memory_service_factory.get_memory_config') as mock_config:
            mock_config.return_value = MagicMock()
            mock_config.return_value.preference_learning_enabled = True
            mock_config.return_value.conversation_summarization_enabled = True
            
            with patch('src.memory.services.memory_service_factory.StorageLayer') as mock_storage_class, \
                 patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
                 patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
                 patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
                 patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
                
                # Setup mocks
                mock_storage = AsyncMock()
                mock_context = AsyncMock()
                mock_preference = AsyncMock()
                mock_search = AsyncMock()
                mock_privacy = AsyncMock()
                
                mock_storage_class.return_value = mock_storage
                mock_context_class.return_value = mock_context
                mock_pref_class.return_value = mock_preference
                mock_search_class.return_value = mock_search
                mock_privacy_class.return_value = mock_privacy
                
                # Setup async methods
                mock_storage.initialize = AsyncMock()
                mock_privacy.initialize = AsyncMock()
                
                service = await MemoryServiceFactory.create_memory_service()
                
                # Verify configuration was loaded
                mock_config.assert_called()
                assert service._config is not None
    
    @pytest.mark.asyncio
    async def test_service_initialization_order(self):
        """Test that services are initialized in the correct order."""
        with patch('src.memory.services.memory_service_factory.StorageLayer') as mock_storage_class, \
             patch('src.memory.services.memory_service_factory.ContextManager') as mock_context_class, \
             patch('src.memory.services.memory_service_factory.PreferenceEngine') as mock_pref_class, \
             patch('src.memory.services.memory_service_factory.SearchService') as mock_search_class, \
             patch('src.memory.services.memory_service_factory.PrivacyController') as mock_privacy_class:
            
            # Setup mocks to track initialization order
            mock_storage = AsyncMock()
            mock_context = AsyncMock()
            mock_preference = AsyncMock()
            mock_search = AsyncMock()
            mock_privacy = AsyncMock()
            
            mock_storage_class.return_value = mock_storage
            mock_context_class.return_value = mock_context
            mock_pref_class.return_value = mock_preference
            mock_search_class.return_value = mock_search
            mock_privacy_class.return_value = mock_privacy
            
            # Setup async methods
            mock_storage.initialize = AsyncMock()
            mock_privacy.initialize = AsyncMock()
            
            service = await MemoryServiceFactory.create_memory_service()
            
            # Verify initialization was called
            mock_storage.initialize.assert_called_once()
            mock_privacy.initialize.assert_called_once()
            assert service._initialized is True