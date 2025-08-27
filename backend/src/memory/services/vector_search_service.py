"""
Vector search service for semantic search capabilities using embeddings.
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ..models import SearchResult, Conversation, Message
from ..repositories.conversation_repository import get_conversation_repository
from datetime import datetime

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector-based semantic search using embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector search service.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.conversation_repo = get_conversation_repository()
        
        # In-memory vector store for this implementation
        # In production, this would be replaced with a proper vector database
        self._vector_store: Dict[str, Dict] = {}  # user_id -> {conversation_id: {embedding, metadata}}
    
    async def initialize(self):
        """Initialize the sentence transformer model asynchronously."""
        if self._model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                self._executor, 
                lambda: SentenceTransformer(self.model_name)
            )
            logger.info("Sentence transformer model loaded successfully")
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a given text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Numpy array representing the text embedding
        """
        await self.initialize()
        
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self._model.get_sentence_embedding_dimension())
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            self._executor,
            lambda: self._model.encode(text.strip(), convert_to_numpy=True)
        )
        
        return embedding
    
    async def generate_conversation_embedding(self, conversation: Conversation) -> np.ndarray:
        """
        Generate embedding for an entire conversation.
        
        Args:
            conversation: Conversation to generate embedding for
            
        Returns:
            Numpy array representing the conversation embedding
        """
        # Combine conversation summary and recent messages for embedding
        text_parts = []
        
        # Add summary if available
        if conversation.summary:
            text_parts.append(conversation.summary)
        
        # Add recent messages (limit to avoid very long texts)
        recent_messages = conversation.messages[-10:]  # Last 10 messages
        for message in recent_messages:
            text_parts.append(f"{message.role.value}: {message.content}")
        
        # Combine all text parts
        combined_text = " ".join(text_parts)
        
        return await self.generate_embedding(combined_text)
    
    async def index_conversation(self, user_id: str, conversation: Conversation) -> None:
        """
        Index a conversation for vector search.
        
        Args:
            user_id: ID of the user who owns the conversation
            conversation: Conversation to index
        """
        try:
            # Generate embedding for the conversation
            embedding = await self.generate_conversation_embedding(conversation)
            
            # Store in vector store
            if user_id not in self._vector_store:
                self._vector_store[user_id] = {}
            
            self._vector_store[user_id][conversation.id] = {
                'embedding': embedding,
                'conversation_id': conversation.id,
                'timestamp': conversation.timestamp,
                'summary': conversation.summary,
                'tags': conversation.tags,
                'message_count': len(conversation.messages)
            }
            
            logger.debug(f"Indexed conversation {conversation.id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error indexing conversation {conversation.id}: {e}")
            raise
    
    async def remove_from_index(self, user_id: str, conversation_id: str) -> None:
        """
        Remove a conversation from the vector index.
        
        Args:
            user_id: ID of the user who owns the conversation
            conversation_id: ID of the conversation to remove
        """
        try:
            if user_id in self._vector_store and conversation_id in self._vector_store[user_id]:
                del self._vector_store[user_id][conversation_id]
                logger.debug(f"Removed conversation {conversation_id} from index for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error removing conversation {conversation_id} from index: {e}")
            raise
    
    async def semantic_search(self, user_id: str, query_text: str, limit: int = 10) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            user_id: ID of the user to search conversations for
            query_text: Text query to search for
            limit: Maximum number of results to return
            
        Returns:
            List of search results ranked by semantic similarity
        """
        try:
            # Check if user has any indexed conversations
            if user_id not in self._vector_store or not self._vector_store[user_id]:
                logger.debug(f"No indexed conversations found for user {user_id}")
                return []
            
            # Generate embedding for the query
            query_embedding = await self.generate_embedding(query_text)
            
            # Calculate similarities with all indexed conversations
            similarities = []
            for conv_id, conv_data in self._vector_store[user_id].items():
                similarity = self._calculate_cosine_similarity(
                    query_embedding, 
                    conv_data['embedding']
                )
                
                similarities.append({
                    'conversation_id': conv_id,
                    'similarity': similarity,
                    'metadata': conv_data
                })
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Convert to SearchResult objects
            results = []
            for item in similarities[:limit]:
                if item['similarity'] > 0.1:  # Minimum similarity threshold
                    result = SearchResult(
                        conversation_id=item['conversation_id'],
                        relevance_score=float(item['similarity']),
                        timestamp=item['metadata']['timestamp'],
                        content_snippet=item['metadata']['summary'] or "No summary available",
                        topics=item['metadata']['tags'],
                        metadata={
                            'search_type': 'semantic',
                            'similarity_score': float(item['similarity']),
                            'message_count': item['metadata']['message_count']
                        }
                    )
                    results.append(result)
            
            logger.debug(f"Semantic search returned {len(results)} results for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search for user {user_id}: {e}")
            return []
    
    async def get_similar_conversations(self, user_id: str, conversation_id: str, limit: int = 5) -> List[SearchResult]:
        """
        Find conversations similar to the given one.
        
        Args:
            user_id: ID of the user who owns the conversations
            conversation_id: ID of the reference conversation
            limit: Maximum number of similar conversations to return
            
        Returns:
            List of similar conversations ranked by similarity
        """
        try:
            # Check if the reference conversation is indexed
            if (user_id not in self._vector_store or 
                conversation_id not in self._vector_store[user_id]):
                logger.debug(f"Reference conversation {conversation_id} not found in index")
                return []
            
            reference_embedding = self._vector_store[user_id][conversation_id]['embedding']
            
            # Calculate similarities with other conversations
            similarities = []
            for conv_id, conv_data in self._vector_store[user_id].items():
                if conv_id == conversation_id:
                    continue  # Skip the reference conversation itself
                
                similarity = self._calculate_cosine_similarity(
                    reference_embedding,
                    conv_data['embedding']
                )
                
                similarities.append({
                    'conversation_id': conv_id,
                    'similarity': similarity,
                    'metadata': conv_data
                })
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Convert to SearchResult objects
            results = []
            for item in similarities[:limit]:
                if item['similarity'] > 0.2:  # Higher threshold for similarity search
                    result = SearchResult(
                        conversation_id=item['conversation_id'],
                        relevance_score=float(item['similarity']),
                        timestamp=item['metadata']['timestamp'],
                        content_snippet=item['metadata']['summary'] or "No summary available",
                        topics=item['metadata']['tags'],
                        metadata={
                            'search_type': 'similarity',
                            'similarity_score': float(item['similarity']),
                            'reference_conversation_id': conversation_id,
                            'message_count': item['metadata']['message_count']
                        }
                    )
                    results.append(result)
            
            logger.debug(f"Found {len(results)} similar conversations for {conversation_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar conversations for {conversation_id}: {e}")
            return []
    
    def _calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            # Check for NaN or infinite values
            if np.any(np.isnan(embedding1)) or np.any(np.isnan(embedding2)):
                return 0.0
            if np.any(np.isinf(embedding1)) or np.any(np.isinf(embedding2)):
                return 0.0
            
            # Normalize the vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Check for NaN result
            if np.isnan(similarity) or np.isinf(similarity):
                return 0.0
            
            # Ensure the result is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def get_index_stats(self, user_id: str) -> Dict:
        """
        Get statistics about the vector index for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing index statistics
        """
        if user_id not in self._vector_store:
            return {
                'indexed_conversations': 0,
                'total_embeddings': 0,
                'embedding_dimension': 0
            }
        
        user_conversations = self._vector_store[user_id]
        embedding_dim = 0
        
        if user_conversations:
            # Get embedding dimension from first conversation
            first_conv = next(iter(user_conversations.values()))
            embedding_dim = len(first_conv['embedding'])
        
        return {
            'indexed_conversations': len(user_conversations),
            'total_embeddings': len(user_conversations),
            'embedding_dimension': embedding_dim
        }
    
    async def reindex_user_conversations(self, user_id: str) -> int:
        """
        Reindex all conversations for a user.
        
        Args:
            user_id: ID of the user whose conversations to reindex
            
        Returns:
            Number of conversations reindexed
        """
        try:
            # Clear existing index for user
            if user_id in self._vector_store:
                del self._vector_store[user_id]
            
            # Get all conversations for the user
            conversations = await self.conversation_repo.get_user_conversations(
                user_id=user_id,
                limit=None  # Get all conversations
            )
            
            # Index each conversation
            indexed_count = 0
            for conversation in conversations:
                await self.index_conversation(user_id, conversation)
                indexed_count += 1
            
            logger.info(f"Reindexed {indexed_count} conversations for user {user_id}")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Error reindexing conversations for user {user_id}: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)