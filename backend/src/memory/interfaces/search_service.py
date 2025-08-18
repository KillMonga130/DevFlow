"""
Search service interface.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models import SearchQuery, SearchResult


class SearchServiceInterface(ABC):
    """Interface for conversation search functionality."""
    
    @abstractmethod
    async def search_conversations(self, query: SearchQuery) -> List[SearchResult]:
        """Search through conversations using the provided query."""
        pass
    
    @abstractmethod
    async def index_conversation(self, user_id: str, conversation_id: str, content: str) -> None:
        """Index a conversation for search."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, user_id: str, conversation_id: str) -> None:
        """Remove a conversation from the search index."""
        pass
    
    @abstractmethod
    async def semantic_search(self, user_id: str, query_text: str, limit: int = 10) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        pass
    
    @abstractmethod
    async def get_similar_conversations(self, user_id: str, conversation_id: str, limit: int = 5) -> List[SearchResult]:
        """Find conversations similar to the given one."""
        pass