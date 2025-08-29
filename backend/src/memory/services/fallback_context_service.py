"""
Fallback context service for basic functionality when primary services fail.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from ..interfaces import ContextManagerInterface
from ..models import (
    ConversationContext, Conversation, ConversationSummary, 
    MessageExchange, Message, MessageRole, UserPreferences
)

logger = logging.getLogger(__name__)


class FallbackContextService(ContextManagerInterface):
    """
    Fallback context service that provides basic functionality when primary services fail.
    This service operates with minimal dependencies and graceful degradation.
    """
    
    def __init__(self):
        """Initialize the fallback context service."""
        self._basic_cache: Dict[str, Dict[str, Any]] = {}
        self._max_cache_size = 100
        self._max_messages_per_user = 20
        
    async def build_context(self, user_id: str, current_message: str) -> ConversationContext:
        """Build basic conversation context with minimal functionality."""
        try:
            # Get cached data if available
            user_data = self._basic_cache.get(user_id, {})
            recent_messages = user_data.get('recent_messages', [])
            
            # Create basic context with available data
            context = ConversationContext(
                user_id=user_id,
                recent_messages=recent_messages[-10:],  # Last 10 messages only
                relevant_history=[],  # No historical context in fallback mode
                user_preferences=self._get_default_preferences(user_id),
                context_summary=self._generate_basic_summary(recent_messages, current_message),
                context_timestamp=datetime.now(timezone.utc)
            )
            
            logger.info(f"Built fallback context for user {user_id} with {len(recent_messages)} messages")
            return context
            
        except Exception as e:
            logger.error(f"Error in fallback context building for user {user_id}: {e}")
            # Return absolute minimal context with default preferences
            return ConversationContext(
                user_id=user_id,
                user_preferences=self._get_default_preferences(user_id),
                context_summary="Fallback mode - limited context available",
                context_timestamp=datetime.now(timezone.utc)
            )
    
    async def summarize_conversation(self, conversation: Conversation) -> ConversationSummary:
        """Create basic conversation summary."""
        try:
            if not conversation.messages:
                return ConversationSummary(
                    conversation_id=conversation.id,
                    timestamp=conversation.timestamp,
                    summary_text="Empty conversation",
                    message_count=0
                )
            
            # Basic extractive summary - just take first and last messages
            first_msg = conversation.messages[0].content[:100] + "..." if len(conversation.messages[0].content) > 100 else conversation.messages[0].content
            last_msg = conversation.messages[-1].content[:100] + "..." if len(conversation.messages[-1].content) > 100 else conversation.messages[-1].content
            
            summary_text = f"Started with: {first_msg}"
            if len(conversation.messages) > 1:
                summary_text += f" | Ended with: {last_msg}"
            
            # Basic topic extraction - just look for common keywords
            key_topics = self._extract_basic_topics(conversation.messages)
            
            return ConversationSummary(
                conversation_id=conversation.id,
                timestamp=conversation.timestamp,
                summary_text=summary_text,
                key_topics=key_topics,
                importance_score=0.5,  # Default importance
                message_count=len(conversation.messages)
            )
            
        except Exception as e:
            logger.error(f"Error in fallback conversation summarization: {e}")
            return ConversationSummary(
                conversation_id=conversation.id,
                timestamp=conversation.timestamp,
                summary_text=f"Fallback summary - {len(conversation.messages)} messages",
                message_count=len(conversation.messages)
            )
    
    async def update_context(self, user_id: str, new_exchange: MessageExchange) -> None:
        """Update context with new message exchange using basic caching."""
        try:
            # Initialize user data if not exists
            if user_id not in self._basic_cache:
                self._basic_cache[user_id] = {'recent_messages': []}
            
            user_data = self._basic_cache[user_id]
            recent_messages = user_data['recent_messages']
            
            # Add new messages
            if new_exchange.user_message:
                recent_messages.append(new_exchange.user_message)
            if new_exchange.assistant_message:
                recent_messages.append(new_exchange.assistant_message)
            
            # Limit message count
            if len(recent_messages) > self._max_messages_per_user:
                recent_messages = recent_messages[-self._max_messages_per_user:]
                user_data['recent_messages'] = recent_messages
            
            # Update timestamp
            user_data['last_updated'] = datetime.now(timezone.utc)
            
            # Manage cache size
            self._manage_cache_size()
            
            logger.debug(f"Updated fallback context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating fallback context for user {user_id}: {e}")
    
    async def prune_old_context(self, user_id: str) -> None:
        """Prune old context data in fallback mode."""
        try:
            if user_id in self._basic_cache:
                user_data = self._basic_cache[user_id]
                last_updated = user_data.get('last_updated')
                
                if last_updated:
                    age_hours = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
                    
                    # Remove if older than 2 hours
                    if age_hours > 2:
                        del self._basic_cache[user_id]
                        logger.info(f"Pruned old fallback context for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error pruning fallback context for user {user_id}: {e}")
    
    async def get_relevant_history(self, user_id: str, current_message: str, limit: int = 5) -> List[ConversationSummary]:
        """Get relevant history - returns empty list in fallback mode."""
        logger.info(f"Fallback mode: No historical context available for user {user_id}")
        return []
    
    def _get_default_preferences(self, user_id: str) -> UserPreferences:
        """Get default user preferences for fallback mode."""
        from ..models.preferences import ResponseStyle, CommunicationPreferences, CommunicationTone, ResponseStyleType
        
        return UserPreferences(
            user_id=user_id,
            response_style=ResponseStyle(
                style_type=ResponseStyleType.CONVERSATIONAL,
                tone=CommunicationTone.HELPFUL,
                preferred_length="medium"
            ),
            communication_preferences=CommunicationPreferences(
                language_preference="en",
                timezone="UTC"
            ),
            last_updated=datetime.now(timezone.utc)
        )
    
    def _generate_basic_summary(self, recent_messages: List[Message], current_message: str) -> str:
        """Generate basic context summary."""
        try:
            if not recent_messages:
                return f"New conversation - Current: {current_message[:50]}..."
            
            message_count = len(recent_messages)
            last_message_time = recent_messages[-1].timestamp if recent_messages else datetime.now(timezone.utc)
            time_ago = (datetime.now(timezone.utc) - last_message_time).total_seconds() / 60
            
            summary = f"Fallback mode: {message_count} recent messages"
            
            if time_ago < 60:
                summary += f" | Last message {int(time_ago)} minutes ago"
            else:
                summary += f" | Last message {int(time_ago/60)} hours ago"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating basic summary: {e}")
            return "Fallback mode - basic context"
    
    def _extract_basic_topics(self, messages: List[Message]) -> List[str]:
        """Extract basic topics using simple keyword matching."""
        try:
            # Combine all user messages
            text = " ".join([msg.content for msg in messages if msg.role == MessageRole.USER])
            text_lower = text.lower()
            
            # Basic topic patterns
            topic_patterns = {
                'programming': ['code', 'coding', 'program', 'function', 'script'],
                'help': ['help', 'assist', 'support', 'problem'],
                'question': ['what', 'how', 'why', 'when', 'where'],
                'error': ['error', 'bug', 'issue', 'problem', 'fix'],
                'learning': ['learn', 'teach', 'explain', 'understand']
            }
            
            topics = []
            for topic, keywords in topic_patterns.items():
                if any(keyword in text_lower for keyword in keywords):
                    topics.append(topic)
            
            return topics[:5]  # Limit to 5 topics
            
        except Exception as e:
            logger.error(f"Error extracting basic topics: {e}")
            return ['general']
    
    def _manage_cache_size(self) -> None:
        """Manage cache size to prevent memory issues."""
        try:
            if len(self._basic_cache) > self._max_cache_size:
                # Remove oldest entries
                sorted_users = sorted(
                    self._basic_cache.items(),
                    key=lambda x: x[1].get('last_updated', datetime.min.replace(tzinfo=timezone.utc))
                )
                
                # Remove oldest 20% of entries
                remove_count = int(self._max_cache_size * 0.2)
                for user_id, _ in sorted_users[:remove_count]:
                    del self._basic_cache[user_id]
                
                logger.info(f"Pruned {remove_count} entries from fallback cache")
                
        except Exception as e:
            logger.error(f"Error managing fallback cache size: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on fallback service."""
        return {
            "service": "fallback_context_service",
            "status": "healthy",
            "cache_size": len(self._basic_cache),
            "max_cache_size": self._max_cache_size,
            "mode": "fallback"
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the fallback cache."""
        try:
            total_messages = sum(
                len(user_data.get('recent_messages', []))
                for user_data in self._basic_cache.values()
            )
            
            return {
                "cached_users": len(self._basic_cache),
                "total_cached_messages": total_messages,
                "average_messages_per_user": total_messages / len(self._basic_cache) if self._basic_cache else 0,
                "cache_utilization": len(self._basic_cache) / self._max_cache_size
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}