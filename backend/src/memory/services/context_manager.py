"""
Context manager service implementation.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import Counter
from ..interfaces import ContextManagerInterface
from ..models import (
    ConversationContext, Conversation, ConversationSummary, 
    MessageExchange, Message, MessageRole
)
from .storage_layer import StorageLayer

logger = logging.getLogger(__name__)


class ContextManager(ContextManagerInterface):
    """Context manager service implementation."""
    
    def __init__(self, storage_layer: Optional[StorageLayer] = None):
        """Initialize the context manager."""
        self._storage = storage_layer or StorageLayer()
        self._context_cache: Dict[str, ConversationContext] = {}
        self._max_context_messages = 50  # Maximum messages to keep in context
        self._max_context_age_days = 30  # Maximum age of context in days
        self._summary_threshold = 20  # Messages threshold for summarization
    
    async def build_context(self, user_id: str, current_message: str) -> ConversationContext:
        """Build conversation context for a user."""
        try:
            # Check cache first
            if user_id in self._context_cache:
                cached_context = self._context_cache[user_id]
                # Check if cache is still valid (less than 5 minutes old)
                if (datetime.now(timezone.utc) - cached_context.context_timestamp).seconds < 300:
                    return cached_context
            
            # Get recent conversations
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self._max_context_age_days)
            
            conversations = await self._storage.get_user_conversations(
                user_id, 
                limit=10,  # Get last 10 conversations
                start_date=start_date,
                end_date=end_date
            )
            
            # Get user preferences
            user_preferences = await self._storage.get_user_preferences(user_id)
            
            # Build recent messages list
            recent_messages = []
            for conv in conversations[-3:]:  # Last 3 conversations
                recent_messages.extend(conv.get_latest_messages(10))
            
            # Sort by timestamp and limit
            recent_messages.sort(key=lambda m: m.timestamp)
            recent_messages = recent_messages[-self._max_context_messages:]
            
            # Get relevant historical summaries
            relevant_history = await self.get_relevant_history(user_id, current_message)
            
            # Generate context summary
            context_summary = self._generate_context_summary(recent_messages, relevant_history)
            
            # Create context object
            context = ConversationContext(
                user_id=user_id,
                recent_messages=recent_messages,
                relevant_history=relevant_history,
                user_preferences=user_preferences,
                context_summary=context_summary,
                context_timestamp=datetime.now(timezone.utc)
            )
            
            # Cache the context
            self._context_cache[user_id] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Error building context for user {user_id}: {str(e)}")
            # Return minimal context on error
            return ConversationContext(
                user_id=user_id,
                context_summary="Error retrieving context",
                context_timestamp=datetime.now(timezone.utc)
            )
    
    async def summarize_conversation(self, conversation: Conversation) -> ConversationSummary:
        """Summarize a conversation using extractive and abstractive techniques."""
        try:
            if not conversation.messages:
                return ConversationSummary(
                    conversation_id=conversation.id,
                    timestamp=conversation.timestamp,
                    summary_text="Empty conversation",
                    message_count=0
                )
            
            # Extract key topics from messages
            key_topics = self._extract_key_topics(conversation.messages)
            
            # Generate summary text
            summary_text = self._generate_summary_text(conversation.messages, key_topics)
            
            # Calculate importance score
            importance_score = self._calculate_importance_score(conversation)
            
            return ConversationSummary(
                conversation_id=conversation.id,
                timestamp=conversation.timestamp,
                summary_text=summary_text,
                key_topics=key_topics,
                importance_score=importance_score,
                message_count=len(conversation.messages),
                metadata={
                    'duration_seconds': conversation.metadata.duration_seconds,
                    'total_tokens': conversation.metadata.total_tokens,
                    'language': conversation.metadata.language
                }
            )
            
        except Exception as e:
            logger.error(f"Error summarizing conversation {conversation.id}: {str(e)}")
            return ConversationSummary(
                conversation_id=conversation.id,
                timestamp=conversation.timestamp,
                summary_text=f"Error summarizing conversation: {str(e)}",
                message_count=len(conversation.messages)
            )
    
    async def update_context(self, user_id: str, new_exchange: MessageExchange) -> None:
        """Update context with a new message exchange."""
        try:
            # Update cached context if it exists
            if user_id in self._context_cache:
                context = self._context_cache[user_id]
                
                # Add new messages to recent messages
                context.add_recent_message(new_exchange.user_message)
                context.add_recent_message(new_exchange.assistant_message)
                
                # Prune if too many messages
                if len(context.recent_messages) > self._max_context_messages:
                    context.recent_messages = context.recent_messages[-self._max_context_messages:]
                
                # Update timestamp
                context.context_timestamp = datetime.now(timezone.utc)
                
                # Regenerate context summary
                context.context_summary = self._generate_context_summary(
                    context.recent_messages, 
                    context.relevant_history
                )
            
        except Exception as e:
            logger.error(f"Error updating context for user {user_id}: {str(e)}")
            # Clear cache on error to force rebuild
            if user_id in self._context_cache:
                del self._context_cache[user_id]
    
    async def prune_old_context(self, user_id: str) -> None:
        """Remove old context data to manage memory usage."""
        try:
            # Remove from cache if too old
            if user_id in self._context_cache:
                context = self._context_cache[user_id]
                age_minutes = (datetime.now(timezone.utc) - context.context_timestamp).total_seconds() / 60
                
                if age_minutes > 30:  # Remove if older than 30 minutes
                    del self._context_cache[user_id]
                    logger.info(f"Pruned old context for user {user_id}")
            
            # Clean up old conversation summaries in storage
            summaries = await self._storage.get_conversation_summaries(user_id)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self._max_context_age_days)
            
            old_summaries = [s for s in summaries if s.timestamp < cutoff_date]
            for summary in old_summaries:
                # Note: This would require a delete method in storage layer
                logger.info(f"Would prune old summary {summary.conversation_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error pruning context for user {user_id}: {str(e)}")
    
    async def get_relevant_history(self, user_id: str, current_message: str, limit: int = 5) -> List[ConversationSummary]:
        """Get relevant historical context for the current message using intelligent selection."""
        try:
            # Get all conversation summaries for the user
            all_summaries = await self._storage.get_conversation_summaries(user_id, limit=50)
            
            if not all_summaries:
                return []
            
            # Analyze current message for context clues
            current_analysis = self._analyze_message_context(current_message)
            
            # Score summaries using multiple relevance factors
            scored_summaries = []
            
            for summary in all_summaries:
                # Calculate multiple relevance scores
                semantic_score = self._calculate_semantic_relevance(current_analysis, summary)
                temporal_score = self._calculate_temporal_relevance(summary)
                importance_score = summary.importance_score
                topic_continuity_score = self._calculate_topic_continuity(current_analysis, summary)
                
                # Weighted combination of scores
                final_score = (
                    semantic_score * 0.4 +
                    topic_continuity_score * 0.3 +
                    importance_score * 0.2 +
                    temporal_score * 0.1
                )
                
                scored_summaries.append((summary, final_score, {
                    'semantic': semantic_score,
                    'temporal': temporal_score,
                    'importance': importance_score,
                    'continuity': topic_continuity_score
                }))
            
            # Apply intelligent filtering
            filtered_summaries = self._apply_intelligent_filtering(scored_summaries, current_analysis)
            
            # Sort by final score and return top results
            filtered_summaries.sort(key=lambda x: x[1], reverse=True)
            
            # Ensure diversity in selected summaries
            diverse_summaries = self._ensure_topic_diversity(filtered_summaries, limit)
            
            return [summary for summary, _, _ in diverse_summaries]
            
        except Exception as e:
            logger.error(f"Error getting relevant history for user {user_id}: {str(e)}")
            return []
    
    def _analyze_message_context(self, message: str) -> Dict[str, Any]:
        """Analyze a message to extract context clues for relevance matching."""
        analysis = {
            'keywords': self._extract_keywords(message),
            'intent': self._classify_message_intent(message),
            'topics': self._extract_topics_from_text(message),
            'complexity': self._assess_message_complexity(message),
            'question_type': self._classify_question_type(message),
            'urgency': self._assess_urgency(message)
        }
        return analysis
    
    def _classify_message_intent(self, message: str) -> str:
        """Classify the intent of a message."""
        message_lower = message.lower()
        
        # Gratitude patterns (check first as they're most specific)
        gratitude_patterns = ['thank you', 'thanks', 'appreciate', 'grateful', 'much appreciated']
        if any(pattern in message_lower for pattern in gratitude_patterns):
            return 'gratitude'
        
        # Learning patterns (check before general question patterns)
        if any(word in message_lower for word in ['explain', 'teach', 'learn', 'understand']):
            return 'learning'
        
        # Question patterns (specific question starters)
        elif any(message_lower.startswith(word) for word in ['what', 'how', 'why', 'when', 'where', 'which', 'who']):
            return 'question'
        
        # Help request patterns
        elif any(word in message_lower for word in ['help', 'assist', 'support']):
            return 'help_request'
        
        # Problem report patterns
        elif any(word in message_lower for word in ['problem', 'error', 'issue', 'bug', 'trouble']):
            return 'problem_report'
        
        # General question pattern (ends with ?)
        elif message_lower.endswith('?'):
            return 'question'
        
        else:
            return 'statement'
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract topics from text using pattern matching and keywords."""
        topics = []
        text_lower = text.lower()
        
        # Technical topics
        tech_patterns = {
            'programming': ['code', 'coding', 'program', 'programming', 'script', 'function', 'method'],
            'data_structures': ['list', 'dict', 'array', 'tree', 'graph', 'stack', 'queue'],
            'algorithms': ['algorithm', 'sort', 'search', 'optimize', 'complexity', 'recursive'],
            'web_development': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'web', 'frontend', 'backend'],
            'database': ['database', 'sql', 'query', 'table', 'schema', 'mongodb', 'postgresql'],
            'machine_learning': ['ml', 'ai', 'model', 'training', 'neural', 'deep learning', 'tensorflow'],
            'debugging': ['debug', 'error', 'exception', 'traceback', 'bug', 'fix', 'troubleshoot']
        }
        
        for topic, keywords in tech_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _assess_message_complexity(self, message: str) -> float:
        """Assess the complexity level of a message."""
        score = 0.0
        
        # Length factor
        score += min(1.0, len(message) / 500.0) * 0.3
        
        # Technical terms
        technical_terms = ['algorithm', 'implementation', 'optimization', 'architecture', 'framework']
        tech_count = sum(1 for term in technical_terms if term in message.lower())
        score += min(1.0, tech_count / 3.0) * 0.4
        
        # Code patterns
        if any(pattern in message for pattern in ['def ', 'class ', 'import ', '()', '{}']):
            score += 0.3
        
        return min(1.0, score)
    
    def _classify_question_type(self, message: str) -> str:
        """Classify the type of question being asked."""
        message_lower = message.lower()
        
        if message_lower.startswith('how'):
            return 'procedural'
        elif message_lower.startswith('what'):
            return 'definitional'
        elif message_lower.startswith('why'):
            return 'explanatory'
        elif message_lower.startswith('when'):
            return 'temporal'
        elif message_lower.startswith('where'):
            return 'locational'
        elif message_lower.startswith('which'):
            return 'comparative'
        elif message_lower.startswith('who'):
            return 'personal'
        else:
            return 'general'
    
    def _assess_urgency(self, message: str) -> float:
        """Assess the urgency level of a message."""
        urgency_indicators = ['urgent', 'asap', 'immediately', 'quickly', 'emergency', 'critical', 'deadline']
        message_lower = message.lower()
        
        urgency_count = sum(1 for indicator in urgency_indicators if indicator in message_lower)
        return min(1.0, urgency_count * 0.5)
    
    def _calculate_semantic_relevance(self, current_analysis: Dict[str, Any], 
                                    summary: ConversationSummary) -> float:
        """Calculate semantic relevance between current message and summary."""
        score = 0.0
        
        # Keyword overlap
        current_keywords = set(current_analysis['keywords'])
        summary_keywords = set(self._extract_keywords(summary.summary_text))
        
        if current_keywords and summary_keywords:
            overlap = len(current_keywords & summary_keywords)
            score += (overlap / len(current_keywords)) * 0.4
        
        # Topic overlap
        current_topics = set(current_analysis['topics'])
        summary_topics = set(summary.key_topics)
        
        if current_topics and summary_topics:
            topic_overlap = len(current_topics & summary_topics)
            score += (topic_overlap / len(current_topics)) * 0.6
        
        return min(1.0, score)
    
    def _calculate_temporal_relevance(self, summary: ConversationSummary) -> float:
        """Calculate temporal relevance based on recency."""
        age_days = (datetime.now(timezone.utc) - summary.timestamp).days
        
        # Exponential decay over 30 days
        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.8
        elif age_days <= 14:
            return 0.6
        elif age_days <= 30:
            return 0.4
        else:
            return 0.2
    
    def _calculate_topic_continuity(self, current_analysis: Dict[str, Any], 
                                  summary: ConversationSummary) -> float:
        """Calculate topic continuity score."""
        # Intent matching
        intent_score = 0.0
        current_intent = current_analysis['intent']
        
        # Map intents to summary patterns
        intent_patterns = {
            'question': ['question', 'ask', 'inquiry'],
            'help_request': ['help', 'assist', 'support'],
            'problem_report': ['problem', 'error', 'issue', 'bug'],
            'learning': ['learn', 'teach', 'explain', 'understand']
        }
        
        if current_intent in intent_patterns:
            patterns = intent_patterns[current_intent]
            if any(pattern in summary.summary_text.lower() for pattern in patterns):
                intent_score = 0.8
        
        # Complexity matching
        complexity_score = 0.0
        current_complexity = current_analysis['complexity']
        
        # Estimate summary complexity from metadata
        summary_complexity = min(1.0, summary.message_count / 20.0)
        
        # Prefer similar complexity levels
        complexity_diff = abs(current_complexity - summary_complexity)
        complexity_score = max(0.0, 1.0 - complexity_diff)
        
        return (intent_score * 0.6) + (complexity_score * 0.4)
    
    def _apply_intelligent_filtering(self, scored_summaries: List[tuple], 
                                   current_analysis: Dict[str, Any]) -> List[tuple]:
        """Apply intelligent filtering to remove irrelevant summaries."""
        filtered = []
        
        for summary, score, score_breakdown in scored_summaries:
            # Filter out very low relevance summaries
            if score < 0.1:
                continue
            
            # Filter based on intent mismatch for specific cases
            current_intent = current_analysis['intent']
            if current_intent == 'gratitude' and score_breakdown['semantic'] < 0.2:
                continue
            
            # Filter very old summaries unless they're highly relevant
            age_days = (datetime.now(timezone.utc) - summary.timestamp).days
            if age_days > 60 and score < 0.5:
                continue
            
            filtered.append((summary, score, score_breakdown))
        
        return filtered
    
    def _ensure_topic_diversity(self, scored_summaries: List[tuple], limit: int) -> List[tuple]:
        """Ensure diversity in selected summaries to avoid topic clustering."""
        if len(scored_summaries) <= limit:
            return scored_summaries
        
        selected = []
        used_topics = set()
        
        # First pass: select highest scoring summaries with unique topics
        for summary, score, score_breakdown in scored_summaries:
            if len(selected) >= limit:
                break
            
            summary_topics = set(summary.key_topics)
            
            # Check for topic overlap with already selected summaries
            if not summary_topics & used_topics or len(selected) == 0:
                selected.append((summary, score, score_breakdown))
                used_topics.update(summary_topics)
        
        # Second pass: fill remaining slots with highest scoring summaries
        remaining_slots = limit - len(selected)
        if remaining_slots > 0:
            remaining_summaries = [s for s in scored_summaries if s not in selected]
            selected.extend(remaining_summaries[:remaining_slots])
        
        return selected
    
    async def get_context_for_conversation(self, user_id: str, conversation_id: str) -> ConversationContext:
        """Get context specifically for a conversation continuation."""
        try:
            # Get the specific conversation
            conversation = await self._storage.get_conversation(conversation_id)
            if not conversation:
                return await self.build_context(user_id, "")
            
            # Get the last few messages from the conversation
            recent_messages = conversation.get_latest_messages(10)
            
            # Get relevant historical context excluding the current conversation
            all_summaries = await self._storage.get_conversation_summaries(user_id, limit=20)
            relevant_summaries = [s for s in all_summaries if s.conversation_id != conversation_id]
            
            # Analyze the conversation to understand context needs
            if recent_messages:
                last_message = recent_messages[-1].content
                current_analysis = self._analyze_message_context(last_message)
                
                # Score and filter relevant summaries
                scored_summaries = []
                for summary in relevant_summaries:
                    relevance_score = self._calculate_semantic_relevance(current_analysis, summary)
                    temporal_score = self._calculate_temporal_relevance(summary)
                    final_score = (relevance_score * 0.7) + (temporal_score * 0.3)
                    scored_summaries.append((summary, final_score))
                
                scored_summaries.sort(key=lambda x: x[1], reverse=True)
                relevant_history = [s for s, _ in scored_summaries[:5]]
            else:
                relevant_history = []
            
            # Get user preferences
            user_preferences = await self._storage.get_user_preferences(user_id)
            
            # Generate context summary
            context_summary = self._generate_conversation_context_summary(conversation, relevant_history)
            
            return ConversationContext(
                user_id=user_id,
                recent_messages=recent_messages,
                relevant_history=relevant_history,
                user_preferences=user_preferences,
                context_summary=context_summary,
                context_timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error getting context for conversation {conversation_id}: {str(e)}")
            return await self.build_context(user_id, "")
    
    def _generate_conversation_context_summary(self, conversation: Conversation, 
                                             relevant_history: List[ConversationSummary]) -> str:
        """Generate context summary for a specific conversation."""
        summary_parts = []
        
        # Current conversation info
        if conversation.messages:
            message_count = len(conversation.messages)
            summary_parts.append(f"Current conversation: {message_count} messages")
            
            # Add conversation topics if available
            if conversation.metadata.topics:
                summary_parts.append(f"Topics: {', '.join(conversation.metadata.topics[:3])}")
        
        # Historical context
        if relevant_history:
            summary_parts.append(f"Related history: {len(relevant_history)} conversations")
            
            # Add most relevant historical topics
            all_topics = []
            for summary in relevant_history[:3]:  # Top 3 most relevant
                all_topics.extend(summary.key_topics)
            
            if all_topics:
                from collections import Counter
                top_topics = [topic for topic, _ in Counter(all_topics).most_common(3)]
                summary_parts.append(f"Historical topics: {', '.join(top_topics)}")
        
        return " | ".join(summary_parts) if summary_parts else "New conversation"
    
    async def refresh_context_cache(self, user_id: str) -> None:
        """Refresh the cached context for a user."""
        try:
            if user_id in self._context_cache:
                del self._context_cache[user_id]
                logger.info(f"Refreshed context cache for user {user_id}")
        except Exception as e:
            logger.error(f"Error refreshing context cache for user {user_id}: {str(e)}")
    
    async def get_context_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about the user's context and conversation history."""
        try:
            # Get conversation summaries
            summaries = await self._storage.get_conversation_summaries(user_id, limit=100)
            
            # Get recent conversations
            conversations = await self._storage.get_user_conversations(user_id, limit=10)
            
            # Calculate statistics
            stats = {
                'total_conversations': len(summaries),
                'recent_conversations': len(conversations),
                'total_messages': sum(s.message_count for s in summaries),
                'average_messages_per_conversation': 0,
                'most_common_topics': [],
                'conversation_frequency': {},
                'context_cache_status': user_id in self._context_cache
            }
            
            if summaries:
                stats['average_messages_per_conversation'] = stats['total_messages'] / len(summaries)
                
                # Analyze topics
                all_topics = []
                for summary in summaries:
                    all_topics.extend(summary.key_topics)
                
                if all_topics:
                    from collections import Counter
                    topic_counts = Counter(all_topics)
                    stats['most_common_topics'] = [
                        {'topic': topic, 'count': count} 
                        for topic, count in topic_counts.most_common(10)
                    ]
                
                # Analyze conversation frequency by day
                from collections import defaultdict
                frequency_by_day = defaultdict(int)
                for summary in summaries[-30:]:  # Last 30 conversations
                    day = summary.timestamp.strftime('%Y-%m-%d')
                    frequency_by_day[day] += 1
                
                stats['conversation_frequency'] = dict(frequency_by_day)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting context statistics for user {user_id}: {str(e)}")
            return {
                'error': str(e),
                'context_cache_status': user_id in self._context_cache
            }
    
    def _extract_key_topics(self, messages: List[Message]) -> List[str]:
        """Extract key topics from conversation messages."""
        # Combine all message content
        text = " ".join([msg.content for msg in messages if msg.role == MessageRole.USER])
        
        # Extract keywords using simple frequency analysis
        keywords = self._extract_keywords(text)
        
        # Group related keywords into topics
        topics = []
        for keyword in keywords[:10]:  # Top 10 keywords
            if len(keyword) > 3 and keyword.isalpha():  # Filter short and non-alphabetic
                topics.append(keyword.lower())
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using simple frequency analysis."""
        # Simple keyword extraction - in production, use more sophisticated NLP
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'can',
            'could', 'should', 'would', 'will', 'shall', 'may', 'might', 'must',
            'have', 'has', 'had', 'been', 'being', 'are', 'was', 'were', 'you',
            'your', 'yours', 'they', 'them', 'their', 'theirs', 'she', 'her',
            'hers', 'him', 'his', 'its', 'our', 'ours', 'myself', 'yourself',
            'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves',
            'want', 'need', 'get', 'got', 'like', 'just', 'now', 'then', 'also',
            'only', 'know', 'think', 'see', 'make', 'way', 'come', 'good', 'new',
            'first', 'last', 'long', 'great', 'little', 'own', 'other', 'old',
            'right', 'big', 'high', 'different', 'small', 'large', 'next', 'early',
            'young', 'important', 'few', 'public', 'bad', 'same', 'able'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Count frequency and return most common
        word_counts = Counter(filtered_words)
        return [word for word, _ in word_counts.most_common(20)]
    
    def _generate_summary_text(self, messages: List[Message], key_topics: List[str]) -> str:
        """Generate summary text from messages and topics using advanced summarization."""
        if not messages:
            return "No messages in conversation"
        
        # Separate user and assistant messages
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]
        
        # Extract key information using multiple techniques
        summary_parts = []
        
        # 1. Topic-based summary
        if key_topics:
            primary_topics = key_topics[:3]  # Focus on top 3 topics
            summary_parts.append(f"Main topics: {', '.join(primary_topics)}")
        
        # 2. Conversation flow analysis
        conversation_flow = self._analyze_conversation_flow(messages)
        if conversation_flow:
            summary_parts.append(conversation_flow)
        
        # 3. Key question-answer pairs
        key_exchanges = self._extract_key_exchanges(user_messages, assistant_messages)
        if key_exchanges:
            summary_parts.extend(key_exchanges)
        
        # 4. Outcome or resolution
        outcome = self._identify_conversation_outcome(messages)
        if outcome:
            summary_parts.append(f"Outcome: {outcome}")
        
        # 5. Statistical summary
        stats = f"{len(user_messages)} questions, {len(assistant_messages)} responses"
        if messages:
            duration = (messages[-1].timestamp - messages[0].timestamp).total_seconds() / 60
            if duration > 1:
                stats += f", {duration:.1f} minutes"
        summary_parts.append(stats)
        
        return " | ".join(summary_parts)
    
    def _analyze_conversation_flow(self, messages: List[Message]) -> Optional[str]:
        """Analyze the flow and progression of the conversation."""
        if len(messages) < 4:
            return None
        
        # Look for patterns in conversation progression
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        
        # Detect conversation type based on patterns
        question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who']
        help_words = ['help', 'assist', 'support', 'guide', 'explain']
        problem_words = ['problem', 'issue', 'error', 'bug', 'trouble', 'stuck']
        
        first_msg = user_messages[0].content.lower() if user_messages else ""
        
        if any(word in first_msg for word in help_words):
            return "Help-seeking conversation"
        elif any(word in first_msg for word in problem_words):
            return "Problem-solving discussion"
        elif any(first_msg.startswith(word) for word in question_words):
            return "Information-seeking dialogue"
        elif "learn" in first_msg or "teach" in first_msg:
            return "Learning-focused interaction"
        else:
            return "General discussion"
    
    def _extract_key_exchanges(self, user_messages: List[Message], 
                             assistant_messages: List[Message]) -> List[str]:
        """Extract the most important question-answer exchanges."""
        if not user_messages or not assistant_messages:
            return []
        
        key_exchanges = []
        
        # Find the most important user questions based on length and keywords
        important_questions = []
        for msg in user_messages:
            importance = self._calculate_message_importance(msg)
            important_questions.append((msg, importance))
        
        # Sort by importance and take top 2
        important_questions.sort(key=lambda x: x[1], reverse=True)
        top_questions = important_questions[:2]
        
        for question, _ in top_questions:
            # Find corresponding assistant response
            question_time = question.timestamp
            corresponding_response = None
            
            for response in assistant_messages:
                if response.timestamp > question_time:
                    corresponding_response = response
                    break
            
            if corresponding_response:
                # Create concise exchange summary
                q_summary = self._summarize_message(question.content, max_length=50)
                a_summary = self._summarize_message(corresponding_response.content, max_length=80)
                key_exchanges.append(f"Q: {q_summary} | A: {a_summary}")
        
        return key_exchanges
    
    def _calculate_message_importance(self, message: Message) -> float:
        """Calculate importance score for a message."""
        content = message.content.lower()
        score = 0.0
        
        # Length factor (longer messages often more important)
        score += min(1.0, len(content) / 200.0) * 0.3
        
        # Question words increase importance
        question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'can', 'could', 'would']
        question_count = sum(1 for word in question_words if word in content)
        score += min(1.0, question_count / 3.0) * 0.3
        
        # Technical terms increase importance
        technical_indicators = ['error', 'problem', 'code', 'function', 'method', 'class', 'variable', 
                              'algorithm', 'data', 'structure', 'implement', 'debug', 'optimize']
        tech_count = sum(1 for term in technical_indicators if term in content)
        score += min(1.0, tech_count / 5.0) * 0.2
        
        # Urgency indicators
        urgency_words = ['urgent', 'important', 'critical', 'asap', 'quickly', 'immediately']
        if any(word in content for word in urgency_words):
            score += 0.2
        
        return min(1.0, score)
    
    def _summarize_message(self, content: str, max_length: int = 100) -> str:
        """Create a concise summary of a message."""
        if len(content) <= max_length:
            return content
        
        # Try to find a natural break point
        sentences = content.split('. ')
        if sentences and len(sentences[0]) <= max_length:
            return sentences[0] + ('.' if not sentences[0].endswith('.') else '')
        
        # Fallback to truncation with ellipsis
        return content[:max_length-3] + "..."
    
    def _identify_conversation_outcome(self, messages: List[Message]) -> Optional[str]:
        """Identify the outcome or resolution of the conversation."""
        if len(messages) < 2:
            return None
        
        # Look at the last few messages for resolution indicators
        last_messages = messages[-3:]
        last_content = " ".join([msg.content.lower() for msg in last_messages])
        
        # Positive resolution indicators
        positive_indicators = [
            'thank', 'thanks', 'helpful', 'solved', 'fixed', 'working', 'perfect',
            'great', 'excellent', 'understand', 'clear', 'got it', 'makes sense'
        ]
        
        # Negative resolution indicators
        negative_indicators = [
            'still not', 'still have', 'not working', 'confused', 'unclear',
            'not sure', 'problem persists', 'still stuck'
        ]
        
        # Neutral/continuation indicators
        continuation_indicators = [
            'will try', 'let me', 'going to', 'next time', 'later', 'continue'
        ]
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in last_content)
        negative_count = sum(1 for indicator in negative_indicators if indicator in last_content)
        continuation_count = sum(1 for indicator in continuation_indicators if indicator in last_content)
        
        if positive_count > negative_count and positive_count > 0:
            return "Successfully resolved"
        elif negative_count > positive_count and negative_count > 0:
            return "Unresolved issues remain"
        elif continuation_count > 0:
            return "Ongoing discussion"
        else:
            return "Discussion concluded"
    
    def _calculate_importance_score(self, conversation: Conversation) -> float:
        """Calculate importance score for a conversation."""
        score = 0.0
        
        # Message count factor (more messages = more important)
        message_count = len(conversation.messages)
        score += min(1.0, message_count / 20.0) * 0.3
        
        # Duration factor (longer conversations = more important)
        if conversation.metadata.duration_seconds:
            duration_minutes = conversation.metadata.duration_seconds / 60
            score += min(1.0, duration_minutes / 30.0) * 0.2
        
        # Token count factor (more content = more important)
        if conversation.metadata.total_tokens:
            score += min(1.0, conversation.metadata.total_tokens / 5000.0) * 0.2
        
        # Topic diversity factor
        if conversation.metadata.topics:
            topic_diversity = min(1.0, len(conversation.metadata.topics) / 5.0)
            score += topic_diversity * 0.2
        
        # Recency factor (more recent = slightly more important)
        age_days = (datetime.now(timezone.utc) - conversation.timestamp).days
        recency_factor = max(0.1, 1.0 - (age_days / 30.0))
        score += recency_factor * 0.1
        
        return min(1.0, score)  # Cap at 1.0
    
    def _calculate_relevance_score(self, current_keywords: List[str], 
                                 summary_topics: List[str], 
                                 summary_text: str) -> float:
        """Calculate relevance score between current message and historical summary."""
        if not current_keywords:
            return 0.0
        
        score = 0.0
        
        # Topic overlap score
        if summary_topics:
            topic_overlap = len(set(current_keywords) & set(summary_topics))
            score += (topic_overlap / len(current_keywords)) * 0.6
        
        # Text similarity score (simple keyword matching)
        summary_keywords = self._extract_keywords(summary_text)
        if summary_keywords:
            text_overlap = len(set(current_keywords) & set(summary_keywords))
            score += (text_overlap / len(current_keywords)) * 0.4
        
        return min(1.0, score)
    
    def _generate_context_summary(self, recent_messages: List[Message], 
                                relevant_history: List[ConversationSummary]) -> str:
        """Generate a summary of the current context."""
        summary_parts = []
        
        if recent_messages:
            summary_parts.append(f"Recent context: {len(recent_messages)} messages")
            
            # Add recent topics
            recent_topics = self._extract_key_topics(recent_messages[-10:])  # Last 10 messages
            if recent_topics:
                summary_parts.append(f"Recent topics: {', '.join(recent_topics[:3])}")
        
        if relevant_history:
            summary_parts.append(f"Relevant history: {len(relevant_history)} conversations")
            
            # Add historical topics
            all_historical_topics = []
            for summary in relevant_history:
                all_historical_topics.extend(summary.key_topics)
            
            if all_historical_topics:
                topic_counts = Counter(all_historical_topics)
                top_topics = [topic for topic, _ in topic_counts.most_common(3)]
                summary_parts.append(f"Historical topics: {', '.join(top_topics)}")
        
        return " | ".join(summary_parts) if summary_parts else "No context available"