"""
Core interfaces for the conversational memory system.
"""

from .memory_service import MemoryServiceInterface
from .context_manager import ContextManagerInterface
from .preference_engine import PreferenceEngineInterface
from .search_service import SearchServiceInterface
from .privacy_controller import PrivacyControllerInterface
from .storage_layer import StorageLayerInterface

__all__ = [
    "MemoryServiceInterface",
    "ContextManagerInterface", 
    "PreferenceEngineInterface",
    "SearchServiceInterface",
    "PrivacyControllerInterface",
    "StorageLayerInterface"
]