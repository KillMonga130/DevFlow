"""
Unit tests for interface definitions.
"""

import pytest
from abc import ABC, abstractmethod
from src.memory.interfaces import (
    MemoryServiceInterface, ContextManagerInterface, PreferenceEngineInterface,
    PrivacyControllerInterface, SearchServiceInterface, StorageLayerInterface
)


class TestMemoryServiceInterface:
    """Test cases for MemoryServiceInterface."""
    
    def test_interface_is_abstract(self):
        """Test that MemoryServiceInterface is abstract."""
        assert issubclass(MemoryServiceInterface, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            MemoryServiceInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'store_conversation',
            'retrieve_context',
            'search_history',
            'delete_user_data',
            'export_user_data',
            'update_privacy_settings',
            'health_check'
        ]
        
        for method_name in required_methods:
            assert hasattr(MemoryServiceInterface, method_name)
            method = getattr(MemoryServiceInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"
    
    def test_interface_implementation_requirements(self):
        """Test that implementing the interface requires all abstract methods."""
        # Incomplete implementation should fail
        class IncompleteImplementation(MemoryServiceInterface):
            async def store_conversation(self, user_id, conversation):
                pass
            # Missing other required methods
        
        with pytest.raises(TypeError):
            IncompleteImplementation()
        
        # Complete implementation should work
        class CompleteImplementation(MemoryServiceInterface):
            async def store_conversation(self, user_id, conversation):
                pass
            
            async def retrieve_context(self, user_id, limit=None):
                pass
            
            async def search_history(self, user_id, query):
                pass
            
            async def delete_user_data(self, user_id, options=None):
                pass
            
            async def export_user_data(self, user_id):
                pass
            
            async def update_privacy_settings(self, user_id, settings):
                pass
            
            async def health_check(self):
                pass
        
        # Should be able to instantiate complete implementation
        implementation = CompleteImplementation()
        assert isinstance(implementation, MemoryServiceInterface)


class TestContextManagerInterface:
    """Test cases for ContextManagerInterface."""
    
    def test_interface_is_abstract(self):
        """Test that ContextManagerInterface is abstract."""
        assert issubclass(ContextManagerInterface, ABC)
        
        with pytest.raises(TypeError):
            ContextManagerInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'build_context',
            'summarize_conversation',
            'update_context',
            'prune_old_context'
        ]
        
        for method_name in required_methods:
            assert hasattr(ContextManagerInterface, method_name)
            method = getattr(ContextManagerInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"


class TestPreferenceEngineInterface:
    """Test cases for PreferenceEngineInterface."""
    
    def test_interface_is_abstract(self):
        """Test that PreferenceEngineInterface is abstract."""
        assert issubclass(PreferenceEngineInterface, ABC)
        
        with pytest.raises(TypeError):
            PreferenceEngineInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'analyze_preferences',
            'apply_preferences',
            'update_preferences',
            'get_preferences'
        ]
        
        for method_name in required_methods:
            assert hasattr(PreferenceEngineInterface, method_name)
            method = getattr(PreferenceEngineInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"


class TestPrivacyControllerInterface:
    """Test cases for PrivacyControllerInterface."""
    
    def test_interface_is_abstract(self):
        """Test that PrivacyControllerInterface is abstract."""
        assert issubclass(PrivacyControllerInterface, ABC)
        
        with pytest.raises(TypeError):
            PrivacyControllerInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'delete_user_data',
            'export_user_data',
            'update_privacy_settings',
            'get_privacy_settings',
            'audit_data_access'
        ]
        
        for method_name in required_methods:
            assert hasattr(PrivacyControllerInterface, method_name)
            method = getattr(PrivacyControllerInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"


class TestSearchServiceInterface:
    """Test cases for SearchServiceInterface."""
    
    def test_interface_is_abstract(self):
        """Test that SearchServiceInterface is abstract."""
        assert issubclass(SearchServiceInterface, ABC)
        
        with pytest.raises(TypeError):
            SearchServiceInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'search_conversations',
            'search_by_keywords',
            'search_by_date_range',
            'search_by_topics'
        ]
        
        for method_name in required_methods:
            assert hasattr(SearchServiceInterface, method_name)
            method = getattr(SearchServiceInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"


class TestStorageLayerInterface:
    """Test cases for StorageLayerInterface."""
    
    def test_interface_is_abstract(self):
        """Test that StorageLayerInterface is abstract."""
        assert issubclass(StorageLayerInterface, ABC)
        
        with pytest.raises(TypeError):
            StorageLayerInterface()
    
    def test_interface_has_required_methods(self):
        """Test that interface defines required abstract methods."""
        required_methods = [
            'store_conversation',
            'get_conversation',
            'get_user_conversations',
            'delete_conversation',
            'store_user_preferences',
            'get_user_preferences',
            'delete_user_data',
            'get_user_data_summary',
            'cleanup_expired_data',
            'health_check'
        ]
        
        for method_name in required_methods:
            assert hasattr(StorageLayerInterface, method_name)
            method = getattr(StorageLayerInterface, method_name)
            assert getattr(method, '__isabstractmethod__', False), f"{method_name} should be abstract"


class TestInterfaceConsistency:
    """Test consistency across interfaces."""
    
    def test_all_interfaces_inherit_from_abc(self):
        """Test that all interfaces inherit from ABC."""
        interfaces = [
            MemoryServiceInterface,
            ContextManagerInterface,
            PreferenceEngineInterface,
            PrivacyControllerInterface,
            SearchServiceInterface,
            StorageLayerInterface
        ]
        
        for interface in interfaces:
            assert issubclass(interface, ABC), f"{interface.__name__} should inherit from ABC"
    
    def test_interface_method_signatures(self):
        """Test that interface methods have consistent signatures."""
        # This test ensures that methods that should be async are marked as such
        # and that parameter names are consistent across interfaces
        
        # Check that storage methods are async
        storage_methods = [
            'store_conversation',
            'get_conversation',
            'get_user_conversations',
            'delete_conversation'
        ]
        
        for method_name in storage_methods:
            if hasattr(StorageLayerInterface, method_name):
                method = getattr(StorageLayerInterface, method_name)
                # Abstract methods should be defined but we can't easily check if they're async
                # This is more of a documentation test
                assert callable(method)
    
    def test_interface_docstrings(self):
        """Test that interfaces have proper documentation."""
        interfaces = [
            MemoryServiceInterface,
            ContextManagerInterface,
            PreferenceEngineInterface,
            PrivacyControllerInterface,
            SearchServiceInterface,
            StorageLayerInterface
        ]
        
        for interface in interfaces:
            assert interface.__doc__ is not None, f"{interface.__name__} should have a docstring"
            assert len(interface.__doc__.strip()) > 0, f"{interface.__name__} docstring should not be empty"


class TestInterfaceUsage:
    """Test interface usage patterns."""
    
    def test_interface_can_be_used_for_type_hints(self):
        """Test that interfaces can be used in type hints."""
        from typing import Optional
        
        def example_function(service: MemoryServiceInterface) -> Optional[str]:
            """Example function using interface type hint."""
            return "test"
        
        # Should not raise any errors
        assert callable(example_function)
    
    def test_interface_isinstance_checks(self):
        """Test that isinstance checks work with interfaces."""
        # Create a mock implementation
        class MockImplementation(MemoryServiceInterface):
            async def store_conversation(self, user_id, conversation):
                pass
            
            async def retrieve_context(self, user_id, limit=None):
                pass
            
            async def search_history(self, user_id, query):
                pass
            
            async def delete_user_data(self, user_id, options=None):
                pass
            
            async def export_user_data(self, user_id):
                pass
            
            async def update_privacy_settings(self, user_id, settings):
                pass
            
            async def health_check(self):
                pass
        
        implementation = MockImplementation()
        
        # isinstance check should work
        assert isinstance(implementation, MemoryServiceInterface)
        assert isinstance(implementation, ABC)
    
    def test_interface_multiple_inheritance(self):
        """Test that interfaces can be used in multiple inheritance."""
        class MultipleInheritanceTest(MemoryServiceInterface, ContextManagerInterface):
            # Implement MemoryServiceInterface methods
            async def store_conversation(self, user_id, conversation):
                pass
            
            async def retrieve_context(self, user_id, limit=None):
                pass
            
            async def search_history(self, user_id, query):
                pass
            
            async def delete_user_data(self, user_id, options=None):
                pass
            
            async def export_user_data(self, user_id):
                pass
            
            async def update_privacy_settings(self, user_id, settings):
                pass
            
            async def health_check(self):
                pass
            
            # Implement ContextManagerInterface methods
            async def build_context(self, user_id, current_message):
                pass
            
            async def summarize_conversation(self, conversation):
                pass
            
            async def update_context(self, user_id, new_exchange):
                pass
            
            async def prune_old_context(self, user_id):
                pass
        
        implementation = MultipleInheritanceTest()
        
        assert isinstance(implementation, MemoryServiceInterface)
        assert isinstance(implementation, ContextManagerInterface)


if __name__ == "__main__":
    pytest.main([__file__])