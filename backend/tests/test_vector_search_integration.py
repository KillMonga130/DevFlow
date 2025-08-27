"""
Integration tests for vector search capabilities.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.memory.services.vector_search_service import VectorSearchService
from src.memory.services.search_service import SearchService
from src.memory.models import (
    SearchQuery, SearchResult, Conversation, Message, 
    MessageRole, ConversationMetadata, MessageMetadata
)


class TestVectorSearchService:
    """Test cases for VectorSearchService."""
    
    @pytest.fixture
    def vector_search_service(self):
        """Create a VectorSearchService instance for testing."""
        return VectorSearchService(model_name="all-MiniLM-L6-v2")
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        now = datetime.now(timezone.utc)
        
        conversations = [
            Conversation(
                id="conv1",
                user_id="user123",
                timestamp=now - timedelta(days=1),
                messages=[
                    Message(
                        id="msg1",
                        role=MessageRole.USER,
                        content="I need help with Python programming and data structures",
                        timestamp=now - timedelta(days=1)
                    ),
                    Message(
                        id="msg2",
                        role=MessageRole.ASSISTANT,
                        content="I can help you with Python programming. What specific data structures are you interested in?",
                        timestamp=now - timedelta(days=1, minutes=-1)
                    )
                ],
                summary="Discussion about Python programming and data structures",
                tags=["python", "programming", "data-structures"]
            ),
            Conversation(
                id="conv2",
                user_id="user123",
                timestamp=now - timedelta(days=2),
                messages=[
                    Message(
                        id="msg3",
                        role=MessageRole.USER,
                        content="How do I implement machine learning algorithms in Python?",
                        timestamp=now - timedelta(days=2)
                    ),
                    Message(
                        id="msg4",
                        role=MessageRole.ASSISTANT,
                        content="There are several ways to implement ML algorithms in Python. You can use libraries like scikit-learn, TensorFlow, or PyTorch.",
                        timestamp=now - timedelta(days=2, minutes=-1)
                    )
                ],
                summary="Machine learning implementation in Python",
                tags=["python", "machine-learning", "algorithms"]
            ),
            Conversation(
                id="conv3",
                user_id="user123",
                timestamp=now - timedelta(days=3),
                messages=[
                    Message(
                        id="msg5",
                        role=MessageRole.USER,
                        content="What are the best practices for JavaScript web development?",
                        timestamp=now - timedelta(days=3)
                    ),
                    Message(
                        id="msg6",
                        role=MessageRole.ASSISTANT,
                        content="JavaScript web development best practices include using modern ES6+ features, proper error handling, and following MVC patterns.",
                        timestamp=now - timedelta(days=3, minutes=-1)
                    )
                ],
                summary="JavaScript web development best practices",
                tags=["javascript", "web-development", "best-practices"]
            )
        ]
        
        return conversations
    
    @pytest.mark.asyncio
    async def test_initialize_model(self, vector_search_service):
        """Test model initialization."""
        # Mock the SentenceTransformer to avoid downloading the actual model
        with patch('src.memory.services.vector_search_service.SentenceTransformer') as mock_transformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_transformer.return_value = mock_model
            
            await vector_search_service.initialize()
            
            assert vector_search_service._model is not None
            mock_transformer.assert_called_once_with("all-MiniLM-L6-v2")
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self, vector_search_service):
        """Test embedding generation for text."""
        # Mock the model and its encode method
        mock_model = MagicMock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_model.get_sentence_embedding_dimension.return_value = 4
        
        vector_search_service._model = mock_model
        
        text = "This is a test sentence"
        embedding = await vector_search_service.generate_embedding(text)
        
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 4
        np.testing.assert_array_equal(embedding, mock_embedding)
        mock_model.encode.assert_called_once_with(text, convert_to_numpy=True)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, vector_search_service):
        """Test embedding generation for empty text."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        vector_search_service._model = mock_model
        
        embedding = await vector_search_service.generate_embedding("")
        
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384
        assert np.all(embedding == 0)  # Should be zero vector
    
    @pytest.mark.asyncio
    async def test_generate_conversation_embedding(self, vector_search_service, sample_conversations):
        """Test embedding generation for entire conversation."""
        # Mock the model
        mock_model = MagicMock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        
        vector_search_service._model = mock_model
        
        conversation = sample_conversations[0]
        embedding = await vector_search_service.generate_conversation_embedding(conversation)
        
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 4
        
        # Verify that the model was called with combined text
        mock_model.encode.assert_called_once()
        called_text = mock_model.encode.call_args[0][0]
        
        # Should include summary and message content
        assert "Discussion about Python programming" in called_text
        assert "Python programming and data structures" in called_text
    
    @pytest.mark.asyncio
    async def test_index_conversation(self, vector_search_service, sample_conversations):
        """Test conversation indexing."""
        # Mock the embedding generation
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        with patch.object(vector_search_service, 'generate_conversation_embedding', return_value=mock_embedding):
            conversation = sample_conversations[0]
            await vector_search_service.index_conversation("user123", conversation)
            
            # Check that conversation is stored in vector store
            assert "user123" in vector_search_service._vector_store
            assert "conv1" in vector_search_service._vector_store["user123"]
            
            stored_data = vector_search_service._vector_store["user123"]["conv1"]
            assert stored_data['conversation_id'] == "conv1"
            assert stored_data['summary'] == conversation.summary
            assert stored_data['tags'] == conversation.tags
            np.testing.assert_array_equal(stored_data['embedding'], mock_embedding)
    
    @pytest.mark.asyncio
    async def test_remove_from_index(self, vector_search_service, sample_conversations):
        """Test conversation removal from index."""
        # First index a conversation
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        with patch.object(vector_search_service, 'generate_conversation_embedding', return_value=mock_embedding):
            conversation = sample_conversations[0]
            await vector_search_service.index_conversation("user123", conversation)
            
            # Verify it's indexed
            assert "conv1" in vector_search_service._vector_store["user123"]
            
            # Remove from index
            await vector_search_service.remove_from_index("user123", "conv1")
            
            # Verify it's removed
            assert "conv1" not in vector_search_service._vector_store["user123"]
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, vector_search_service, sample_conversations):
        """Test semantic search functionality."""
        # Mock embeddings
        query_embedding = np.array([0.8, 0.1, 0.1, 0.0])  # Similar to first conversation
        conv1_embedding = np.array([0.9, 0.1, 0.0, 0.0])  # High similarity
        conv2_embedding = np.array([0.1, 0.9, 0.0, 0.0])  # Low similarity
        
        # Index conversations with mocked embeddings
        vector_search_service._vector_store["user123"] = {
            "conv1": {
                'embedding': conv1_embedding,
                'conversation_id': "conv1",
                'timestamp': sample_conversations[0].timestamp,
                'summary': sample_conversations[0].summary,
                'tags': sample_conversations[0].tags,
                'message_count': len(sample_conversations[0].messages)
            },
            "conv2": {
                'embedding': conv2_embedding,
                'conversation_id': "conv2",
                'timestamp': sample_conversations[1].timestamp,
                'summary': sample_conversations[1].summary,
                'tags': sample_conversations[1].tags,
                'message_count': len(sample_conversations[1].messages)
            }
        }
        
        # Mock query embedding generation
        with patch.object(vector_search_service, 'generate_embedding', return_value=query_embedding):
            results = await vector_search_service.semantic_search("user123", "Python programming", limit=5)
            
            assert len(results) == 2
            
            # Results should be sorted by similarity (conv1 should be first)
            assert results[0].conversation_id == "conv1"
            assert results[1].conversation_id == "conv2"
            
            # Check that similarity scores are calculated
            assert results[0].relevance_score > results[1].relevance_score
            assert results[0].metadata['search_type'] == 'semantic'
            assert 'similarity_score' in results[0].metadata
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_results(self, vector_search_service):
        """Test semantic search with no indexed conversations."""
        results = await vector_search_service.semantic_search("user456", "test query")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_similar_conversations(self, vector_search_service, sample_conversations):
        """Test finding similar conversations."""
        # Mock embeddings - conv1 and conv2 are similar, conv3 is different
        conv1_embedding = np.array([0.9, 0.1, 0.0, 0.0])
        conv2_embedding = np.array([0.8, 0.2, 0.0, 0.0])  # Similar to conv1
        conv3_embedding = np.array([0.1, 0.1, 0.9, 0.0])  # Different
        
        # Index conversations
        vector_search_service._vector_store["user123"] = {
            "conv1": {
                'embedding': conv1_embedding,
                'conversation_id': "conv1",
                'timestamp': sample_conversations[0].timestamp,
                'summary': sample_conversations[0].summary,
                'tags': sample_conversations[0].tags,
                'message_count': len(sample_conversations[0].messages)
            },
            "conv2": {
                'embedding': conv2_embedding,
                'conversation_id': "conv2",
                'timestamp': sample_conversations[1].timestamp,
                'summary': sample_conversations[1].summary,
                'tags': sample_conversations[1].tags,
                'message_count': len(sample_conversations[1].messages)
            },
            "conv3": {
                'embedding': conv3_embedding,
                'conversation_id': "conv3",
                'timestamp': sample_conversations[2].timestamp,
                'summary': sample_conversations[2].summary,
                'tags': sample_conversations[2].tags,
                'message_count': len(sample_conversations[2].messages)
            }
        }
        
        # Find conversations similar to conv1
        results = await vector_search_service.get_similar_conversations("user123", "conv1", limit=5)
        
        # Should return conv2 (similar) but not conv3 (different) or conv1 (self)
        assert len(results) == 1
        assert results[0].conversation_id == "conv2"
        assert results[0].metadata['search_type'] == 'similarity'
        assert results[0].metadata['reference_conversation_id'] == "conv1"
    
    @pytest.mark.asyncio
    async def test_get_similar_conversations_not_found(self, vector_search_service):
        """Test finding similar conversations when reference doesn't exist."""
        results = await vector_search_service.get_similar_conversations("user123", "nonexistent", limit=5)
        assert len(results) == 0
    
    def test_calculate_cosine_similarity(self, vector_search_service):
        """Test cosine similarity calculation."""
        # Test identical vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        similarity = vector_search_service._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6
        
        # Test orthogonal vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        similarity = vector_search_service._calculate_cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-6
        
        # Test opposite vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        similarity = vector_search_service._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0  # Should be clamped to 0
        
        # Test zero vectors
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        similarity = vector_search_service._calculate_cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, vector_search_service, sample_conversations):
        """Test getting index statistics."""
        # Test empty index
        stats = await vector_search_service.get_index_stats("user123")
        assert stats['indexed_conversations'] == 0
        assert stats['total_embeddings'] == 0
        assert stats['embedding_dimension'] == 0
        
        # Index a conversation
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        with patch.object(vector_search_service, 'generate_conversation_embedding', return_value=mock_embedding):
            await vector_search_service.index_conversation("user123", sample_conversations[0])
            
            stats = await vector_search_service.get_index_stats("user123")
            assert stats['indexed_conversations'] == 1
            assert stats['total_embeddings'] == 1
            assert stats['embedding_dimension'] == 4
    
    @pytest.mark.asyncio
    async def test_reindex_user_conversations(self, vector_search_service, sample_conversations):
        """Test reindexing all user conversations."""
        # Mock the conversation repository
        mock_repo = AsyncMock()
        mock_repo.get_user_conversations.return_value = sample_conversations
        vector_search_service.conversation_repo = mock_repo
        
        # Mock embedding generation
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        with patch.object(vector_search_service, 'generate_conversation_embedding', return_value=mock_embedding):
            indexed_count = await vector_search_service.reindex_user_conversations("user123")
            
            assert indexed_count == 3
            assert len(vector_search_service._vector_store["user123"]) == 3
            
            # Verify all conversations are indexed
            for conv in sample_conversations:
                assert conv.id in vector_search_service._vector_store["user123"]


class TestSearchServiceVectorIntegration:
    """Test cases for SearchService integration with vector search."""
    
    @pytest.fixture
    def search_service(self):
        """Create a SearchService instance for testing."""
        return SearchService()
    
    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        now = datetime.now(timezone.utc)
        
        return [
            Conversation(
                id="conv1",
                user_id="user123",
                timestamp=now - timedelta(days=1),
                messages=[
                    Message(
                        id="msg1",
                        role=MessageRole.USER,
                        content="I need help with Python programming",
                        timestamp=now - timedelta(days=1)
                    )
                ],
                summary="Python programming help",
                tags=["python", "programming"]
            ),
            Conversation(
                id="conv2",
                user_id="user123",
                timestamp=now - timedelta(days=2),
                messages=[
                    Message(
                        id="msg2",
                        role=MessageRole.USER,
                        content="Machine learning algorithms in Python",
                        timestamp=now - timedelta(days=2)
                    )
                ],
                summary="Machine learning discussion",
                tags=["python", "machine-learning"]
            )
        ]
    
    @pytest.mark.asyncio
    async def test_index_conversation_integration(self, search_service, sample_conversations):
        """Test conversation indexing through SearchService."""
        conversation = sample_conversations[0]
        
        # Mock the conversation repository
        mock_repo = AsyncMock()
        mock_repo.get_conversation.return_value = conversation
        search_service.conversation_repo = mock_repo
        
        # Mock vector search service
        mock_vector_service = AsyncMock()
        search_service.vector_search_service = mock_vector_service
        
        await search_service.index_conversation("user123", "conv1", "content")
        
        mock_repo.get_conversation.assert_called_once_with("user123", "conv1")
        mock_vector_service.index_conversation.assert_called_once_with("user123", conversation)
    
    @pytest.mark.asyncio
    async def test_semantic_search_integration(self, search_service):
        """Test semantic search through SearchService."""
        # Mock vector search service
        mock_results = [
            SearchResult(
                conversation_id="conv1",
                relevance_score=0.9,
                timestamp=datetime.now(timezone.utc),
                content_snippet="Python programming help",
                topics=["python"],
                metadata={'search_type': 'semantic'}
            )
        ]
        
        mock_vector_service = AsyncMock()
        mock_vector_service.semantic_search.return_value = mock_results
        search_service.vector_search_service = mock_vector_service
        
        results = await search_service.semantic_search("user123", "Python help", limit=10)
        
        assert len(results) == 1
        assert results[0].conversation_id == "conv1"
        mock_vector_service.semantic_search.assert_called_once_with("user123", "Python help", 10)
    
    @pytest.mark.asyncio
    async def test_combined_search_results(self, search_service, sample_conversations):
        """Test combining keyword and semantic search results."""
        # Create mock results from both search types
        # Note: Using same message_id for conv1 results so they get combined
        keyword_results = [
            SearchResult(
                conversation_id="conv1",
                message_id="msg1",
                relevance_score=0.8,
                timestamp=datetime.now(timezone.utc),
                content_snippet="Python programming help",
                topics=["python"]
            )
        ]
        
        semantic_results = [
            SearchResult(
                conversation_id="conv1",
                message_id="msg1",  # Same message_id to trigger combination
                relevance_score=0.7,
                timestamp=datetime.now(timezone.utc),
                content_snippet="Python programming help",
                topics=["python"],
                metadata={'search_type': 'semantic'}
            ),
            SearchResult(
                conversation_id="conv2",
                message_id="msg2",
                relevance_score=0.6,
                timestamp=datetime.now(timezone.utc),
                content_snippet="Machine learning discussion",
                topics=["python", "machine-learning"],
                metadata={'search_type': 'semantic'}
            )
        ]
        
        combined_results = await search_service._combine_search_results(keyword_results, semantic_results)
        
        # Should have 2 results (conv1 combined, conv2 separate)
        assert len(combined_results) == 2
        
        # First result should be conv1 with combined score and both search types
        conv1_result = next(r for r in combined_results if r.conversation_id == "conv1")
        assert 'keyword' in conv1_result.metadata['search_types']
        assert 'semantic' in conv1_result.metadata['search_types']
        assert conv1_result.relevance_score > 0.8  # Should be boosted for dual match
        
        # Second result should be conv2 with only semantic
        conv2_result = next(r for r in combined_results if r.conversation_id == "conv2")
        assert conv2_result.metadata['search_types'] == ['semantic']
    
    @pytest.mark.asyncio
    async def test_search_conversations_with_vector_integration(self, search_service, sample_conversations):
        """Test full search integration with vector search."""
        query = SearchQuery(
            keywords=["python", "programming"],
            user_id="user123",
            limit=10,
            offset=0
        )
        
        # Mock the filtered conversations
        with patch.object(search_service, '_get_filtered_conversations', return_value=sample_conversations):
            # Mock semantic search
            semantic_results = [
                SearchResult(
                    conversation_id="conv2",
                    relevance_score=0.8,
                    timestamp=datetime.now(timezone.utc),
                    content_snippet="Machine learning discussion",
                    topics=["python", "machine-learning"],
                    metadata={'search_type': 'semantic'}
                )
            ]
            
            with patch.object(search_service, 'semantic_search', return_value=semantic_results):
                results = await search_service.search_conversations(query)
                
                # Should return combined results
                assert len(results) > 0
                
                # Verify that semantic search was called
                search_service.semantic_search.assert_called_once()


class TestVectorSearchErrorHandling:
    """Test error handling in vector search functionality."""
    
    @pytest.fixture
    def vector_search_service(self):
        """Create a VectorSearchService instance for testing."""
        return VectorSearchService()
    
    @pytest.mark.asyncio
    async def test_embedding_generation_error(self, vector_search_service):
        """Test error handling in embedding generation."""
        # Mock model to raise an exception
        mock_model = MagicMock()
        mock_model.encode.side_effect = Exception("Model error")
        vector_search_service._model = mock_model
        
        with pytest.raises(Exception):
            await vector_search_service.generate_embedding("test text")
    
    @pytest.mark.asyncio
    async def test_semantic_search_error_handling(self, vector_search_service):
        """Test error handling in semantic search."""
        # Mock generate_embedding to raise an exception
        with patch.object(vector_search_service, 'generate_embedding', side_effect=Exception("Embedding error")):
            results = await vector_search_service.semantic_search("user123", "test query")
            
            # Should return empty list on error
            assert results == []
    
    @pytest.mark.asyncio
    async def test_similarity_calculation_error(self, vector_search_service):
        """Test error handling in similarity calculation."""
        # Test with invalid embeddings
        invalid_embedding = np.array([float('nan'), 0.0, 0.0])
        valid_embedding = np.array([1.0, 0.0, 0.0])
        
        similarity = vector_search_service._calculate_cosine_similarity(invalid_embedding, valid_embedding)
        
        # Should return 0.0 on error
        assert similarity == 0.0
    
    def test_cleanup(self, vector_search_service):
        """Test cleanup functionality."""
        # Should not raise any exceptions
        vector_search_service.cleanup()