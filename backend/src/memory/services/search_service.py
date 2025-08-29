"""
Search service implementation with keyword-based search and relevance scoring.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from collections import Counter
from ..interfaces import SearchServiceInterface
from ..models import SearchQuery, SearchResult, Conversation, Message, DateRange
from ..models.search import SearchResultHighlight
from ..models.conversation import ConversationMetadata
from ..repositories.conversation_repository import get_conversation_repository
from .vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


class SearchService(SearchServiceInterface):
    """Search service implementation with keyword-based search capabilities."""
    
    def __init__(self):
        """Initialize the search service."""
        self.conversation_repo = get_conversation_repository()
        self.vector_search_service = VectorSearchService()
        self._stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'i', 'you', 'we', 'they', 'this',
            'but', 'or', 'not', 'can', 'could', 'would', 'should', 'may',
            'might', 'must', 'shall', 'do', 'does', 'did', 'have', 'had'
        }
    
    async def search_conversations(self, query: SearchQuery) -> List[SearchResult]:
        """Search through conversations using the provided query with keyword matching and relevance scoring."""
        try:
            # Get conversations based on filters
            conversations = await self._get_filtered_conversations(query)
            
            if not conversations:
                return []
            
            # If no keywords provided, return filtered results by date
            if not query.keywords or not any(query.keywords):
                return await self._create_basic_results(conversations, query)
            
            # Perform both keyword-based and semantic search
            keyword_results = []
            semantic_results = []
            
            # Keyword-based search
            for conversation in conversations:
                results = await self._search_in_conversation(conversation, query)
                keyword_results.extend(results)
            
            # Semantic search if we have keywords
            if query.keywords:
                query_text = " ".join(query.keywords)
                semantic_results = await self.semantic_search(query.user_id, query_text, query.limit * 2)
            
            # Combine and deduplicate results
            search_results = await self._combine_search_results(keyword_results, semantic_results)
            
            # Apply advanced ranking with relevance and recency
            search_results = await self._apply_advanced_ranking(search_results, query)
            
            # Apply topic categorization
            search_results = await self._categorize_results_by_topic(search_results, query)
            
            # Apply offset and limit
            start_idx = query.offset
            end_idx = start_idx + query.limit
            
            return search_results[start_idx:end_idx]
            
        except Exception as e:
            logger.error(f"Error in search_conversations: {e}")
            return []
    
    async def index_conversation(self, user_id: str, conversation_id: str, content: str) -> None:
        """Index a conversation for search with vector embeddings."""
        try:
            # Get the full conversation for vector indexing
            conversation = await self.conversation_repo.get_conversation(user_id, conversation_id)
            if conversation:
                await self.vector_search_service.index_conversation(user_id, conversation)
                logger.debug(f"Indexed conversation {conversation_id} for user {user_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for indexing")
        except Exception as e:
            logger.error(f"Error indexing conversation {conversation_id}: {e}")
    
    async def remove_from_index(self, user_id: str, conversation_id: str) -> None:
        """Remove a conversation from the search index."""
        try:
            await self.vector_search_service.remove_from_index(user_id, conversation_id)
            logger.debug(f"Removed conversation {conversation_id} from index for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing conversation {conversation_id} from index: {e}")
    
    async def semantic_search(self, user_id: str, query_text: str, limit: int = 10) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        try:
            results = await self.vector_search_service.semantic_search(user_id, query_text, limit)
            logger.debug(f"Semantic search returned {len(results)} results for query: {query_text}")
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def get_similar_conversations(self, user_id: str, conversation_id: str, limit: int = 5) -> List[SearchResult]:
        """Find conversations similar to the given one."""
        try:
            results = await self.vector_search_service.get_similar_conversations(user_id, conversation_id, limit)
            logger.debug(f"Found {len(results)} similar conversations for {conversation_id}")
            return results
        except Exception as e:
            logger.error(f"Error finding similar conversations: {e}")
            return []
    
    async def _get_filtered_conversations(self, query: SearchQuery) -> List[Conversation]:
        """Get conversations filtered by date range and topics with enhanced filtering."""
        try:
            start_date = None
            end_date = None
            
            if query.date_range:
                start_date = query.date_range.start_date
                end_date = query.date_range.end_date
            
            # Get conversations with basic filtering
            conversations = await self.conversation_repo.get_user_conversations(
                user_id=query.user_id,
                start_date=start_date,
                end_date=end_date,
                tags=query.topics,
                limit=None  # We'll handle pagination after scoring
            )
            
            # Apply additional date range filtering if needed
            if query.date_range:
                conversations = self._apply_enhanced_date_filtering(conversations, query.date_range)
            
            # Apply enhanced topic filtering
            if query.topics:
                conversations = self._apply_enhanced_topic_filtering(conversations, query.topics)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting filtered conversations: {e}")
            return []
    
    def _apply_enhanced_date_filtering(self, conversations: List[Conversation], date_range: DateRange) -> List[Conversation]:
        """Apply enhanced date range filtering with message-level granularity."""
        filtered_conversations = []
        
        for conversation in conversations:
            # Check if conversation timestamp is in range
            if not date_range.contains(conversation.timestamp):
                continue
            
            # Also check if any messages are in the date range
            messages_in_range = []
            for message in conversation.messages:
                if date_range.contains(message.timestamp):
                    messages_in_range.append(message)
            
            # Include conversation if it has messages in the date range
            if messages_in_range:
                # Create a copy of the conversation with only messages in range
                filtered_conversation = Conversation(
                    id=conversation.id,
                    user_id=conversation.user_id,
                    timestamp=conversation.timestamp,
                    messages=messages_in_range,
                    summary=conversation.summary,
                    tags=conversation.tags,
                    metadata=conversation.metadata
                )
                filtered_conversations.append(filtered_conversation)
        
        return filtered_conversations
    
    def _apply_enhanced_topic_filtering(self, conversations: List[Conversation], topics: List[str]) -> List[Conversation]:
        """Apply enhanced topic filtering with fuzzy matching and relevance scoring."""
        if not topics:
            return conversations
        
        filtered_conversations = []
        topic_keywords = [topic.lower() for topic in topics]
        
        for conversation in conversations:
            topic_match_score = 0.0
            
            # Check exact topic matches
            conversation_topics = [tag.lower() for tag in conversation.tags]
            exact_matches = len(set(topic_keywords) & set(conversation_topics))
            topic_match_score += exact_matches * 2.0  # High score for exact matches
            
            # Check partial topic matches in conversation content
            conversation_text = ""
            if conversation.summary:
                conversation_text += conversation.summary + " "
            
            for message in conversation.messages[:5]:  # Check first 5 messages for performance
                conversation_text += message.content + " "
            
            conversation_text = conversation_text.lower()
            
            # Count keyword occurrences in content
            for topic_keyword in topic_keywords:
                if topic_keyword in conversation_text:
                    # Count occurrences but cap the contribution
                    occurrences = min(3, conversation_text.count(topic_keyword))
                    topic_match_score += occurrences * 0.5
            
            # Include conversation if it has any topic relevance
            if topic_match_score > 0:
                # Add topic relevance to metadata
                if conversation.metadata is None:
                    conversation.metadata = ConversationMetadata()
                conversation.metadata.additional_data['topic_relevance_score'] = topic_match_score
                filtered_conversations.append(conversation)
        
        # Sort by topic relevance
        filtered_conversations.sort(
            key=lambda c: c.metadata.additional_data.get('topic_relevance_score', 0) if c.metadata else 0, 
            reverse=True
        )
        
        return filtered_conversations
    
    async def _create_basic_results(self, conversations: List[Conversation], query: SearchQuery) -> List[SearchResult]:
        """Create basic search results without keyword matching."""
        results = []
        
        for conversation in conversations:
            if not conversation.messages:
                continue
                
            # Use the first message as content snippet
            first_message = conversation.messages[0]
            content_snippet = self._truncate_text(first_message.content, 200)
            
            result = SearchResult(
                conversation_id=conversation.id,
                message_id=first_message.id,
                relevance_score=0.5,  # Default score for date-filtered results
                timestamp=conversation.timestamp,
                content_snippet=content_snippet,
                topics=conversation.tags,
                metadata={
                    'message_count': len(conversation.messages),
                    'conversation_summary': conversation.summary
                }
            )
            
            results.append(result)
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
        return results[query.offset:query.offset + query.limit]
    
    async def _search_in_conversation(self, conversation: Conversation, query: SearchQuery) -> List[SearchResult]:
        """Search for keywords within a single conversation."""
        results = []
        keywords = [kw.lower().strip() for kw in query.keywords if kw.strip()]
        
        if not keywords:
            return results
        
        # Search in conversation summary first
        if conversation.summary:
            summary_score = self._calculate_text_relevance(conversation.summary, keywords)
            if summary_score > 0:
                # Boost summary matches but ensure score stays <= 1.0
                boosted_score = min(1.0, summary_score * 1.2)
                result = SearchResult(
                    conversation_id=conversation.id,
                    relevance_score=boosted_score,
                    timestamp=conversation.timestamp,
                    content_snippet=self._truncate_text(conversation.summary, 200),
                    topics=conversation.tags,
                    metadata={
                        'source': 'summary',
                        'message_count': len(conversation.messages)
                    }
                )
                
                # Add highlights for summary
                self._add_highlights(result, conversation.summary, keywords, 'summary')
                results.append(result)
        
        # Search in individual messages
        for message in conversation.messages:
            message_score = self._calculate_text_relevance(message.content, keywords)
            
            if message_score > 0:
                result = SearchResult(
                    conversation_id=conversation.id,
                    message_id=message.id,
                    relevance_score=message_score,
                    timestamp=message.timestamp,
                    content_snippet=self._truncate_text(message.content, 200),
                    topics=conversation.tags,
                    metadata={
                        'source': 'message',
                        'role': message.role.value,
                        'message_tokens': message.metadata.tokens
                    }
                )
                
                # Add highlights for message content
                self._add_highlights(result, message.content, keywords, 'content')
                results.append(result)
        
        return results
    
    def _calculate_text_relevance(self, text: str, keywords: List[str]) -> float:
        """Calculate relevance score for text based on keyword matches."""
        if not text or not keywords:
            return 0.0
        
        text_lower = text.lower()
        text_words = self._tokenize_text(text_lower)
        text_word_count = len(text_words)
        
        if text_word_count == 0:
            return 0.0
        
        # Count keyword matches
        total_matches = 0
        unique_keyword_matches = 0
        keyword_positions = []
        has_phrase_match = False
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_found = False
            
            # Check for exact phrase matching first (with word boundaries for single words)
            if ' ' in keyword_lower:
                # Multi-word phrase - use exact phrase matching
                phrase_matches = len(re.findall(re.escape(keyword_lower), text_lower))
            else:
                # Single word - use word boundaries to avoid partial matches
                phrase_matches = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', text_lower))
            
            if phrase_matches > 0:
                keyword_found = True
                unique_keyword_matches += 1
                total_matches += phrase_matches * 3  # Strong boost for exact phrase matches
                has_phrase_match = True
                
                # Find positions for proximity scoring
                if ' ' in keyword_lower:
                    # Multi-word phrase
                    for match in re.finditer(re.escape(keyword_lower), text_lower):
                        keyword_positions.append(match.start())
                else:
                    # Single word with boundaries
                    for match in re.finditer(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
                        keyword_positions.append(match.start())
            else:
                # Individual word matching only if no phrase match
                keyword_words = self._tokenize_text(keyword_lower)
                word_matches_in_keyword = 0
                
                for word in keyword_words:
                    if word not in self._stop_words and len(word) > 2:  # Ignore very short words
                        word_matches = text_words.count(word)
                        if word_matches > 0:
                            word_matches_in_keyword += word_matches
                            total_matches += word_matches
                
                if word_matches_in_keyword > 0:
                    keyword_found = True
                    unique_keyword_matches += 1
        
        if total_matches == 0:
            return 0.0
        
        # Calculate base relevance score
        # TF (Term Frequency) component
        tf_score = total_matches / text_word_count
        
        # Keyword coverage component (how many unique keywords matched)
        coverage_score = unique_keyword_matches / len(keywords)
        
        # Proximity bonus (keywords appearing close together)
        proximity_bonus = self._calculate_proximity_bonus(keyword_positions, len(text))
        
        # Length penalty (prefer shorter, more focused matches)
        length_penalty = min(1.0, 100 / max(text_word_count, 1))
        
        # Calculate base score
        base_score = (
            tf_score * 0.4 +
            coverage_score * 0.3 +
            proximity_bonus * 0.1 +
            length_penalty * 0.2
        )
        
        # Apply phrase bonus - phrase matches get significant boost
        if has_phrase_match:
            # Give phrase matches a substantial boost to ensure they score higher
            relevance_score = base_score + 0.2
        else:
            # Scale down individual word matches significantly to ensure phrase matches score higher
            relevance_score = base_score * 0.7
        
        # Ensure score is between 0 and 1
        return min(1.0, max(0.0, relevance_score))
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into words, removing punctuation and extra whitespace."""
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        return [word for word in words if len(word) > 1]  # Filter out single characters
    
    def _calculate_proximity_bonus(self, positions: List[int], text_length: int) -> float:
        """Calculate bonus score for keywords appearing close together."""
        if len(positions) < 2:
            return 0.0
        
        positions.sort()
        min_distance = float('inf')
        
        for i in range(len(positions) - 1):
            distance = positions[i + 1] - positions[i]
            min_distance = min(min_distance, distance)
        
        # Normalize distance by text length and invert (closer = higher score)
        if min_distance == float('inf'):
            return 0.0
        
        normalized_distance = min_distance / max(text_length, 1)
        proximity_score = max(0.0, 1.0 - normalized_distance * 10)  # Scale factor of 10
        
        return proximity_score
    
    def _add_highlights(self, result: SearchResult, text: str, keywords: List[str], field: str) -> None:
        """Add highlighted text snippets to search result with enhanced context."""
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Find all matches with different patterns
            matches = []
            
            # Exact phrase matches
            if ' ' in keyword_lower:
                pattern = re.escape(keyword_lower)
                for match in re.finditer(pattern, text_lower):
                    matches.append((match.start(), match.end(), 'exact_phrase'))
            else:
                # Word boundary matches
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                for match in re.finditer(pattern, text_lower):
                    matches.append((match.start(), match.end(), 'exact_word'))
            
            # Process matches and create enhanced highlights
            for start_pos, end_pos, match_type in matches:
                # Get extended context (up to 100 characters on each side)
                context_start = max(0, start_pos - 100)
                context_end = min(len(text), end_pos + 100)
                
                context_before = text[context_start:start_pos]
                highlighted_text = text[start_pos:end_pos]
                context_after = text[end_pos:context_end]
                
                # Improve context boundaries (but ensure we don't lose all context)
                improved_before = self._improve_context_boundary(context_before, is_before=True)
                improved_after = self._improve_context_boundary(context_after, is_before=False)
                
                # Use improved context if it's not empty, otherwise use original
                final_before = improved_before if improved_before.strip() else context_before
                final_after = improved_after if improved_after.strip() else context_after
                
                result.add_highlight(
                    field=field,
                    text=highlighted_text,
                    before=final_before,
                    after=final_after
                )
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length with ellipsis."""
        if len(text) <= max_length:
            return text
        
        # Try to break at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can break at a word boundary reasonably close
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    async def _apply_advanced_ranking(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Apply advanced ranking combining relevance and recency scores."""
        if not results:
            return results
        
        # Calculate recency scores
        now = datetime.now()
        max_age_days = 365  # Consider conversations older than 1 year as having minimal recency score
        
        for result in results:
            # Calculate age in days
            age_days = (now - result.timestamp.replace(tzinfo=None)).days
            
            # Calculate recency score (1.0 for today, decreasing to 0.1 for max_age_days)
            recency_score = max(0.1, 1.0 - (age_days / max_age_days))
            
            # Combine relevance and recency (70% relevance, 30% recency)
            combined_score = (result.relevance_score * 0.7) + (recency_score * 0.3)
            
            # Update the relevance score with combined score
            result.relevance_score = min(1.0, combined_score)
            
            # Add recency information to metadata
            result.metadata['recency_score'] = recency_score
            result.metadata['age_days'] = age_days
        
        # Sort by combined score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    async def _categorize_results_by_topic(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Categorize search results by topics and enhance topic information."""
        if not results:
            return results
        
        # Count topic frequencies across all results
        topic_counts = {}
        for result in results:
            for topic in result.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Sort topics by frequency
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Enhance results with topic categorization
        for result in results:
            # Add topic relevance scores
            topic_scores = {}
            for topic in result.topics:
                # Score based on frequency and query relevance
                frequency_score = topic_counts[topic] / len(results)
                
                # Boost score if topic matches query topics
                query_boost = 1.0
                if query.topics and topic.lower() in [t.lower() for t in query.topics]:
                    query_boost = 1.5
                
                topic_scores[topic] = frequency_score * query_boost
            
            # Add categorization metadata
            result.metadata['topic_scores'] = topic_scores
            result.metadata['primary_topic'] = max(topic_scores.keys(), key=topic_scores.get) if topic_scores else None
            result.metadata['topic_distribution'] = dict(sorted_topics[:5])  # Top 5 topics across all results
        
        return results
    

    def _improve_context_boundary(self, context: str, is_before: bool) -> str:
        """Improve context boundaries by breaking at sentence or clause boundaries."""
        if not context or len(context) < 20:  # Don't process very short contexts
            return context
        
        # Sentence boundary markers
        sentence_markers = ['. ', '! ', '? ', '\n']
        
        if is_before:
            # For context before, find the last sentence boundary
            best_pos = -1
            for marker in sentence_markers:
                last_pos = context.rfind(marker)
                if last_pos > len(context) * 0.2 and last_pos > best_pos:  # Keep more context
                    best_pos = last_pos
            
            if best_pos > -1:
                return context[best_pos + 2:].strip()  # +2 to skip marker and space
        else:
            # For context after, find the first sentence boundary
            best_pos = len(context)
            for marker in sentence_markers:
                first_pos = context.find(marker)
                if first_pos > 10 and first_pos < len(context) * 0.8 and first_pos < best_pos:
                    best_pos = first_pos
            
            if best_pos < len(context):
                return context[:best_pos + 1].strip()
        
        return context
    
    async def _combine_search_results(self, keyword_results: List[SearchResult], semantic_results: List[SearchResult]) -> List[SearchResult]:
        """
        Combine keyword and semantic search results, avoiding duplicates and balancing scores.
        
        Args:
            keyword_results: Results from keyword-based search
            semantic_results: Results from semantic search
            
        Returns:
            Combined and deduplicated list of search results
        """
        # Create a dictionary to track results by conversation_id and message_id
        combined_results = {}
        
        # Add keyword results
        for result in keyword_results:
            key = (result.conversation_id, result.message_id or "")
            if key not in combined_results:
                # Mark as keyword result and boost score slightly
                result.metadata['search_types'] = ['keyword']
                result.metadata['keyword_score'] = result.relevance_score
                combined_results[key] = result
            else:
                # If already exists, update with keyword information
                existing = combined_results[key]
                existing.metadata['search_types'].append('keyword')
                existing.metadata['keyword_score'] = result.relevance_score
        
        # Add semantic results
        for result in semantic_results:
            key = (result.conversation_id, result.message_id or "")
            if key not in combined_results:
                # Mark as semantic result
                result.metadata['search_types'] = ['semantic']
                result.metadata['semantic_score'] = result.relevance_score
                combined_results[key] = result
            else:
                # If already exists, combine scores
                existing = combined_results[key]
                existing.metadata['search_types'].append('semantic')
                existing.metadata['semantic_score'] = result.relevance_score
                
                # Combine scores: give more weight to results that match both keyword and semantic
                keyword_score = existing.metadata.get('keyword_score', 0.0)
                semantic_score = result.relevance_score
                
                # Weighted combination: 60% keyword, 40% semantic, with bonus for dual matches
                combined_score = (keyword_score * 0.6) + (semantic_score * 0.4)
                if len(existing.metadata['search_types']) > 1:
                    combined_score *= 1.2  # 20% bonus for dual matches
                
                existing.relevance_score = min(1.0, combined_score)
        
        # Convert back to list and sort by relevance
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return final_results