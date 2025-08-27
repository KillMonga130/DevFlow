"""
Preference engine service implementation.
"""

import re
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from ..interfaces.preference_engine import PreferenceEngineInterface
from ..models import (
    UserPreferences, Conversation, UserFeedback, Message, MessageRole
)
from ..models.preferences import (
    ResponseStyle, ResponseStyleType, CommunicationTone, TopicInterest, 
    CommunicationPreferences
)
from ..models.common import FeedbackType

logger = logging.getLogger(__name__)


class PreferenceAnalyzer:
    """Analyzes conversation patterns to extract user preferences."""
    
    # Keywords that indicate different response style preferences
    STYLE_KEYWORDS = {
        ResponseStyleType.CONCISE: [
            'brief', 'short', 'concise', 'quick', 'summary', 'tldr', 'tl;dr',
            'in short', 'briefly', 'keep it short', 'just the basics'
        ],
        ResponseStyleType.DETAILED: [
            'detailed', 'explain', 'elaborate', 'comprehensive', 'thorough',
            'in detail', 'step by step', 'walk me through', 'break it down'
        ],
        ResponseStyleType.TECHNICAL: [
            'technical', 'specs', 'documentation', 'implementation', 'code',
            'algorithm', 'architecture', 'deep dive', 'under the hood'
        ],
        ResponseStyleType.CASUAL: [
            'casual', 'simple', 'easy', 'layman', 'plain english', 'eli5',
            'explain like', 'simple terms', 'not too technical'
        ]
    }
    
    TONE_KEYWORDS = {
        CommunicationTone.FRIENDLY: [
            'thanks', 'please', 'appreciate', 'great', 'awesome', 'cool',
            'nice', 'wonderful', 'fantastic', 'amazing'
        ],
        CommunicationTone.PROFESSIONAL: [
            'professional', 'business', 'formal', 'official', 'corporate',
            'enterprise', 'industry', 'standard'
        ],
        CommunicationTone.DIRECT: [
            'direct', 'straight', 'no fluff', 'get to the point', 'bottom line',
            'cut to the chase', 'just tell me', 'simply'
        ]
    }
    
    # Common topic patterns
    TOPIC_PATTERNS = {
        'programming': [
            'code', 'programming', 'software', 'development', 'algorithm',
            'function', 'class', 'method', 'variable', 'debug', 'bug'
        ],
        'web development': [
            'html', 'css', 'javascript', 'react', 'vue', 'angular', 'frontend',
            'backend', 'api', 'rest', 'graphql', 'database'
        ],
        'data science': [
            'data', 'analysis', 'machine learning', 'ai', 'statistics',
            'pandas', 'numpy', 'visualization', 'model', 'dataset'
        ],
        'business': [
            'business', 'strategy', 'marketing', 'sales', 'revenue',
            'profit', 'customer', 'market', 'competition', 'growth'
        ],
        'education': [
            'learn', 'study', 'course', 'tutorial', 'lesson', 'teach',
            'explain', 'understand', 'knowledge', 'skill'
        ]
    }
    
    def analyze_response_style(self, conversations: List[Conversation]) -> ResponseStyle:
        """Analyze conversations to determine preferred response style."""
        style_scores = defaultdict(float)
        tone_scores = defaultdict(float)
        total_messages = 0
        
        for conversation in conversations:
            user_messages = conversation.get_messages_by_role(MessageRole.USER)
            
            for message in user_messages:
                content_lower = message.content.lower()
                total_messages += 1
                
                # Analyze style preferences
                for style_type, keywords in self.STYLE_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in content_lower:
                            style_scores[style_type] += 1
                
                # Analyze tone preferences
                for tone_type, keywords in self.TONE_KEYWORDS.items():
                    for keyword in keywords:
                        if keyword in content_lower:
                            tone_scores[tone_type] += 1
                
                # Analyze message length preference
                message_length = len(message.content.split())
                if message_length < 10:
                    style_scores[ResponseStyleType.CONCISE] += 0.5
                elif message_length > 50:
                    style_scores[ResponseStyleType.DETAILED] += 0.5
        
        # Determine dominant style and tone
        dominant_style = max(style_scores.items(), key=lambda x: x[1])[0] if style_scores else ResponseStyleType.CONVERSATIONAL
        dominant_tone = max(tone_scores.items(), key=lambda x: x[1])[0] if tone_scores else CommunicationTone.HELPFUL
        
        # Calculate confidence based on consistency
        max_style_score = style_scores.get(dominant_style, 0)
        max_tone_score = tone_scores.get(dominant_tone, 0)
        confidence = min(1.0, (max_style_score + max_tone_score) / max(total_messages, 1))
        
        return ResponseStyle(
            style_type=dominant_style,
            tone=dominant_tone,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )
    
    def extract_topics(self, conversations: List[Conversation]) -> List[TopicInterest]:
        """Extract topic interests from conversations."""
        topic_mentions = defaultdict(int)
        topic_contexts = defaultdict(set)
        topic_timestamps = defaultdict(list)
        
        for conversation in conversations:
            user_messages = conversation.get_messages_by_role(MessageRole.USER)
            
            for message in user_messages:
                content_lower = message.content.lower()
                words = re.findall(r'\b\w+\b', content_lower)
                
                # Check for predefined topic patterns
                for topic, keywords in self.TOPIC_PATTERNS.items():
                    matches = sum(1 for keyword in keywords if keyword in content_lower)
                    if matches > 0:
                        topic_mentions[topic] += matches
                        topic_contexts[topic].update(words[:10])  # First 10 words as context
                        topic_timestamps[topic].append(message.timestamp)
                
                # Extract potential new topics from frequent words
                word_freq = Counter(words)
                for word, freq in word_freq.most_common(5):
                    if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'they', 'have', 'will']:
                        topic_mentions[word] += freq
                        topic_contexts[word].update(words[:5])
                        topic_timestamps[word].append(message.timestamp)
        
        # Convert to TopicInterest objects
        topic_interests = []
        total_mentions = sum(topic_mentions.values())
        
        for topic, mentions in topic_mentions.items():
            if mentions >= 2:  # Only include topics mentioned at least twice
                interest_level = min(1.0, mentions / max(total_mentions * 0.1, 1))
                last_mentioned = max(topic_timestamps[topic]) if topic_timestamps[topic] else None
                
                topic_interests.append(TopicInterest(
                    topic=topic,
                    interest_level=interest_level,
                    frequency_mentioned=mentions,
                    last_mentioned=last_mentioned,
                    context_keywords=list(topic_contexts[topic])[:10],  # Limit to 10 keywords
                    created_at=datetime.now(timezone.utc)
                ))
        
        # Sort by interest level and return top 20
        topic_interests.sort(key=lambda x: x.interest_level, reverse=True)
        return topic_interests[:20]
    
    def analyze_communication_preferences(self, conversations: List[Conversation]) -> CommunicationPreferences:
        """Analyze communication style preferences."""
        preferences = {
            'prefers_step_by_step': 0,
            'prefers_code_examples': 0,
            'prefers_analogies': 0,
            'prefers_bullet_points': 0
        }
        
        total_messages = 0
        
        for conversation in conversations:
            user_messages = conversation.get_messages_by_role(MessageRole.USER)
            
            for message in user_messages:
                content_lower = message.content.lower()
                total_messages += 1
                
                # Check for step-by-step preferences
                if any(phrase in content_lower for phrase in [
                    'step by step', 'walk me through', 'one by one', 'first', 'then', 'next'
                ]):
                    preferences['prefers_step_by_step'] += 1
                
                # Check for code example preferences
                if any(phrase in content_lower for phrase in [
                    'example', 'code', 'show me', 'demonstrate', 'sample'
                ]):
                    preferences['prefers_code_examples'] += 1
                
                # Check for analogy preferences
                if any(phrase in content_lower for phrase in [
                    'like', 'similar to', 'analogy', 'compare', 'metaphor'
                ]):
                    preferences['prefers_analogies'] += 1
                
                # Check for bullet point preferences
                if any(phrase in content_lower for phrase in [
                    'list', 'bullet', 'points', 'summary', 'outline'
                ]):
                    preferences['prefers_bullet_points'] += 1
        
        # Calculate confidence based on consistency
        total_preference_signals = sum(preferences.values())
        confidence = min(1.0, total_preference_signals / max(total_messages, 1))
        
        return CommunicationPreferences(
            prefers_step_by_step=preferences['prefers_step_by_step'] > total_messages * 0.2,
            prefers_code_examples=preferences['prefers_code_examples'] > total_messages * 0.3,
            prefers_analogies=preferences['prefers_analogies'] > total_messages * 0.1,
            prefers_bullet_points=preferences['prefers_bullet_points'] > total_messages * 0.2,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )


class PreferenceEngine(PreferenceEngineInterface):
    """Preference engine service implementation."""
    
    def __init__(self):
        """Initialize the preference engine."""
        self.analyzer = PreferenceAnalyzer()
        self._preferences_cache: Dict[str, UserPreferences] = {}
        logger.info("PreferenceEngine initialized")
    
    async def analyze_user_preferences(self, user_id: str, conversations: List[Conversation]) -> UserPreferences:
        """Analyze conversations to extract user preferences."""
        try:
            logger.info(f"Analyzing preferences for user {user_id} from {len(conversations)} conversations")
            
            if not conversations:
                logger.warning(f"No conversations provided for user {user_id}")
                return UserPreferences(user_id=user_id)
            
            # Analyze different aspects of preferences
            response_style = self.analyzer.analyze_response_style(conversations)
            topic_interests = self.analyzer.extract_topics(conversations)
            communication_preferences = self.analyzer.analyze_communication_preferences(conversations)
            
            # Create comprehensive user preferences
            preferences = UserPreferences(
                user_id=user_id,
                response_style=response_style,
                topic_interests=topic_interests,
                communication_preferences=communication_preferences,
                last_updated=datetime.now(timezone.utc),
                learning_enabled=True
            )
            
            # Cache the preferences
            self._preferences_cache[user_id] = preferences
            
            logger.info(f"Successfully analyzed preferences for user {user_id}: "
                       f"{len(topic_interests)} topics, style={response_style.style_type.value}")
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error analyzing preferences for user {user_id}: {str(e)}")
            # Return basic preferences on error
            return UserPreferences(user_id=user_id)
    
    async def apply_preferences(self, user_id: str, response: str) -> str:
        """Apply user preferences to modify a response."""
        try:
            logger.debug(f"Applying preferences for user {user_id}")
            
            # Get user preferences
            preferences = await self.get_preferences(user_id)
            
            if not preferences.learning_enabled:
                logger.debug(f"Learning disabled for user {user_id}, returning original response")
                return response
            
            # Apply response style modifications
            modified_response = await self._apply_response_style(response, preferences.response_style)
            
            # Apply communication preferences
            modified_response = await self._apply_communication_preferences(
                modified_response, preferences.communication_preferences
            )
            
            # Apply tone adjustments
            modified_response = await self._apply_tone_adjustments(
                modified_response, preferences.response_style.tone
            )
            
            logger.debug(f"Successfully applied preferences for user {user_id}")
            return modified_response
            
        except Exception as e:
            logger.error(f"Error applying preferences for user {user_id}: {str(e)}")
            # Return original response on error
            return response
    
    async def update_preferences(self, user_id: str, feedback: UserFeedback) -> None:
        """Update preferences based on user feedback."""
        try:
            logger.info(f"Updating preferences for user {user_id} based on feedback")
            
            # Get current preferences
            current_preferences = await self.get_preferences(user_id)
            
            # Apply feedback to preferences
            await self._apply_feedback_to_preferences(current_preferences, feedback)
            
            # Update cache
            self._preferences_cache[user_id] = current_preferences
            
            # If we have a storage layer, persist the changes
            await self._persist_preferences(user_id, current_preferences)
            
            logger.info(f"Successfully updated preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
            raise
    
    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get current user preferences."""
        # Check cache first
        if user_id in self._preferences_cache:
            return self._preferences_cache[user_id]
        
        # Return basic preferences if not found
        return UserPreferences(user_id=user_id)
    
    async def learn_from_interaction(self, user_id: str, user_message: str, assistant_response: str, feedback: UserFeedback = None) -> None:
        """Learn preferences from a single interaction."""
        try:
            logger.debug(f"Learning from interaction for user {user_id}")
            
            # Get current preferences
            current_preferences = await self.get_preferences(user_id)
            
            # Create a temporary conversation for analysis
            from ..models.conversation import Conversation, Message, MessageRole
            
            temp_conversation = Conversation(
                user_id=user_id,
                messages=[
                    Message(role=MessageRole.USER, content=user_message),
                    Message(role=MessageRole.ASSISTANT, content=assistant_response)
                ]
            )
            
            # Analyze this single interaction
            new_preferences = await self.analyze_user_preferences(user_id, [temp_conversation])
            
            # Merge with existing preferences (weighted towards existing)
            if current_preferences.topic_interests or current_preferences.response_style.confidence > 0:
                # Merge topic interests
                for new_interest in new_preferences.topic_interests:
                    existing_interest = current_preferences.get_topic_interest(new_interest.topic)
                    if existing_interest:
                        # Update existing interest with weighted average
                        new_level = (existing_interest.interest_level * 0.8 + new_interest.interest_level * 0.2)
                        existing_interest.update_interest_level(new_level)
                        existing_interest.increment_frequency()
                    else:
                        # Add new interest with reduced confidence
                        new_interest.interest_level *= 0.3
                        current_preferences.topic_interests.append(new_interest)
                
                # Update response style with weighted average
                if new_preferences.response_style.confidence > 0:
                    current_style_confidence = current_preferences.response_style.confidence
                    new_style_confidence = new_preferences.response_style.confidence * 0.2
                    
                    if new_style_confidence > current_style_confidence * 0.1:  # Only update if significant
                        current_preferences.response_style.confidence = min(1.0, 
                            current_style_confidence * 0.9 + new_style_confidence)
            else:
                # Use new preferences if no existing ones
                current_preferences = new_preferences
            
            # Apply feedback if provided
            if feedback:
                await self._apply_feedback_to_preferences(current_preferences, feedback)
            
            # Update cache
            self._preferences_cache[user_id] = current_preferences
            
            logger.debug(f"Successfully updated preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error learning from interaction for user {user_id}: {str(e)}")
    
    async def _apply_feedback_to_preferences(self, preferences: UserPreferences, feedback: UserFeedback) -> None:
        """Apply user feedback to update preferences."""
        try:
            if feedback.feedback_type == FeedbackType.POSITIVE:
                # Increase confidence in current preferences
                preferences.response_style.confidence = min(1.0, preferences.response_style.confidence * 1.1)
                preferences.communication_preferences.confidence = min(1.0, preferences.communication_preferences.confidence * 1.1)
            
            elif feedback.feedback_type == FeedbackType.NEGATIVE:
                # Decrease confidence in current preferences
                preferences.response_style.confidence = max(0.0, preferences.response_style.confidence * 0.9)
                preferences.communication_preferences.confidence = max(0.0, preferences.communication_preferences.confidence * 0.9)
            
            elif feedback.feedback_type == FeedbackType.CORRECTION and feedback.feedback_text:
                # Analyze correction text for preference hints
                correction_lower = feedback.feedback_text.lower()
                
                # Check for style corrections
                if any(word in correction_lower for word in ['shorter', 'brief', 'concise']):
                    preferences.response_style.style_type = ResponseStyleType.CONCISE
                    preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.2)
                
                elif any(word in correction_lower for word in ['longer', 'detailed', 'elaborate']):
                    preferences.response_style.style_type = ResponseStyleType.DETAILED
                    preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.2)
            
            preferences.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error applying feedback to preferences: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the preferences cache."""
        self._preferences_cache.clear()
        logger.info("Preferences cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._preferences_cache)
    
    async def _apply_response_style(self, response: str, style: ResponseStyle) -> str:
        """Apply response style preferences to modify the response."""
        try:
            if style.confidence < 0.3:  # Low confidence, don't modify
                return response
            
            modified_response = response
            
            # Apply style-specific modifications
            if style.style_type == ResponseStyleType.CONCISE:
                modified_response = await self._make_response_concise(modified_response)
            
            elif style.style_type == ResponseStyleType.DETAILED:
                modified_response = await self._make_response_detailed(modified_response)
            
            elif style.style_type == ResponseStyleType.TECHNICAL:
                modified_response = await self._make_response_technical(modified_response)
            
            elif style.style_type == ResponseStyleType.CASUAL:
                modified_response = await self._make_response_casual(modified_response)
            
            # Apply length preferences
            if style.preferred_length:
                modified_response = await self._adjust_response_length(
                    modified_response, style.preferred_length
                )
            
            return modified_response
            
        except Exception as e:
            logger.error(f"Error applying response style: {str(e)}")
            return response
    
    async def _apply_communication_preferences(self, response: str, prefs: CommunicationPreferences) -> str:
        """Apply communication preferences to modify the response."""
        try:
            if prefs.confidence < 0.3:  # Low confidence, don't modify
                return response
            
            modified_response = response
            
            # Apply step-by-step formatting
            if prefs.prefers_step_by_step:
                modified_response = await self._add_step_by_step_formatting(modified_response)
            
            # Add code examples if preferred
            if prefs.prefers_code_examples:
                modified_response = await self._enhance_with_code_examples(modified_response)
            
            # Add analogies if preferred
            if prefs.prefers_analogies:
                modified_response = await self._add_analogies(modified_response)
            
            # Format with bullet points if preferred
            if prefs.prefers_bullet_points:
                modified_response = await self._add_bullet_point_formatting(modified_response)
            
            return modified_response
            
        except Exception as e:
            logger.error(f"Error applying communication preferences: {str(e)}")
            return response
    
    async def _apply_tone_adjustments(self, response: str, tone: CommunicationTone) -> str:
        """Apply tone adjustments to the response."""
        try:
            modified_response = response
            
            if tone == CommunicationTone.FRIENDLY:
                modified_response = await self._make_tone_friendly(modified_response)
            
            elif tone == CommunicationTone.PROFESSIONAL:
                modified_response = await self._make_tone_professional(modified_response)
            
            elif tone == CommunicationTone.DIRECT:
                modified_response = await self._make_tone_direct(modified_response)
            
            elif tone == CommunicationTone.ENCOURAGING:
                modified_response = await self._make_tone_encouraging(modified_response)
            
            return modified_response
            
        except Exception as e:
            logger.error(f"Error applying tone adjustments: {str(e)}")
            return response
    
    async def _make_response_concise(self, response: str) -> str:
        """Make response more concise."""
        # Simple implementation - remove redundant phrases and shorten sentences
        lines = response.split('\n')
        concise_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove redundant phrases
            redundant_phrases = [
                'As I mentioned before,', 'It should be noted that', 'It is important to understand that',
                'Please note that', 'Keep in mind that', 'It is worth mentioning that'
            ]
            
            for phrase in redundant_phrases:
                line = line.replace(phrase, '').strip()
            
            # Shorten if too long
            if len(line) > 150:
                sentences = line.split('. ')
                if len(sentences) > 1:
                    line = sentences[0] + '.'
            
            concise_lines.append(line)
        
        return '\n'.join(concise_lines)
    
    async def _make_response_detailed(self, response: str) -> str:
        """Make response more detailed."""
        # Add explanatory phrases and encourage elaboration
        if len(response) < 200:  # Only enhance short responses
            detailed_response = response
            
            # Add explanatory context
            if not any(phrase in response.lower() for phrase in ['because', 'since', 'due to', 'this is']):
                detailed_response += "\n\nThis is important because it helps ensure better understanding and implementation."
            
            # Suggest further exploration
            if not response.endswith('?'):
                detailed_response += "\n\nWould you like me to elaborate on any specific aspect of this topic?"
            
            return detailed_response
        
        return response
    
    async def _make_response_technical(self, response: str) -> str:
        """Make response more technical."""
        # Add technical context and precision
        technical_response = response
        
        # Add technical precision phrases
        if 'works' in response.lower() and 'algorithm' not in response.lower():
            technical_response = technical_response.replace('works', 'functions algorithmically')
        
        if 'uses' in response.lower() and 'implements' not in response.lower():
            technical_response = technical_response.replace('uses', 'implements')
        
        return technical_response
    
    async def _make_response_casual(self, response: str) -> str:
        """Make response more casual."""
        # Simplify technical language
        casual_response = response
        
        # Replace formal terms with casual ones
        replacements = {
            'utilize': 'use',
            'implement': 'set up',
            'functionality': 'feature',
            'parameters': 'settings',
            'algorithm': 'method'
        }
        
        for formal, casual in replacements.items():
            casual_response = casual_response.replace(formal, casual)
        
        return casual_response
    
    async def _persist_preferences(self, user_id: str, preferences: UserPreferences) -> None:
        """Persist user preferences to storage."""
        try:
            # For now, this is a placeholder - in a real implementation,
            # this would save to a database or file system
            logger.debug(f"Persisting preferences for user {user_id}")
            
            # TODO: Implement actual persistence when storage layer is available
            # Example: await self.storage.save_preferences(user_id, preferences.to_dict())
            
        except Exception as e:
            logger.error(f"Error persisting preferences for user {user_id}: {str(e)}")
    
    async def load_preferences(self, user_id: str) -> UserPreferences:
        """Load user preferences from storage."""
        try:
            logger.debug(f"Loading preferences for user {user_id}")
            
            # Check cache first
            if user_id in self._preferences_cache:
                return self._preferences_cache[user_id]
            
            # TODO: Implement actual loading when storage layer is available
            # Example: data = await self.storage.load_preferences(user_id)
            # if data:
            #     preferences = UserPreferences.from_dict(data)
            #     self._preferences_cache[user_id] = preferences
            #     return preferences
            
            # Return default preferences if not found
            preferences = UserPreferences(user_id=user_id)
            self._preferences_cache[user_id] = preferences
            return preferences
            
        except Exception as e:
            logger.error(f"Error loading preferences for user {user_id}: {str(e)}")
            return UserPreferences(user_id=user_id)
    
    async def process_correction_feedback(self, user_id: str, original_response: str, 
                                        corrected_response: str, feedback_text: str = None) -> None:
        """Process correction feedback to learn user preferences."""
        try:
            logger.info(f"Processing correction feedback for user {user_id}")
            
            # Analyze the differences between original and corrected responses
            corrections = await self._analyze_correction_differences(original_response, corrected_response)
            
            # Get current preferences
            preferences = await self.get_preferences(user_id)
            
            # Apply corrections to preferences
            await self._apply_corrections_to_preferences(preferences, corrections, feedback_text)
            
            # Update cache and persist
            self._preferences_cache[user_id] = preferences
            await self._persist_preferences(user_id, preferences)
            
            logger.info(f"Successfully processed correction feedback for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing correction feedback for user {user_id}: {str(e)}")
    
    async def _analyze_correction_differences(self, original: str, corrected: str) -> Dict[str, Any]:
        """Analyze differences between original and corrected responses."""
        corrections = {
            'length_change': len(corrected) - len(original),
            'style_indicators': [],
            'tone_indicators': [],
            'format_changes': []
        }
        
        original_lower = original.lower()
        corrected_lower = corrected.lower()
        
        # Analyze length changes
        if corrections['length_change'] < -50:
            corrections['style_indicators'].append('prefers_concise')
        elif corrections['length_change'] > 50:
            corrections['style_indicators'].append('prefers_detailed')
        
        # Analyze formatting changes
        if original.count('\n') < corrected.count('\n'):
            corrections['format_changes'].append('prefers_structured')
        
        if '1.' in corrected and '1.' not in original:
            corrections['format_changes'].append('prefers_numbered_lists')
        
        if '•' in corrected and '•' not in original:
            corrections['format_changes'].append('prefers_bullet_points')
        
        # Analyze tone changes
        friendly_words = ['please', 'thank', 'appreciate', 'hope']
        if sum(1 for word in friendly_words if word in corrected_lower) > sum(1 for word in friendly_words if word in original_lower):
            corrections['tone_indicators'].append('prefers_friendly')
        
        formal_indicators = ['however', 'furthermore', 'therefore', 'consequently']
        if sum(1 for word in formal_indicators if word in corrected_lower) > sum(1 for word in formal_indicators if word in original_lower):
            corrections['tone_indicators'].append('prefers_professional')
        
        return corrections
    
    async def _apply_corrections_to_preferences(self, preferences: UserPreferences, 
                                              corrections: Dict[str, Any], feedback_text: str = None) -> None:
        """Apply correction analysis to user preferences."""
        try:
            # Update response style based on corrections
            if 'prefers_concise' in corrections['style_indicators']:
                preferences.response_style.style_type = ResponseStyleType.CONCISE
                preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.3)
            
            elif 'prefers_detailed' in corrections['style_indicators']:
                preferences.response_style.style_type = ResponseStyleType.DETAILED
                preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.3)
            
            # Update communication preferences
            if 'prefers_numbered_lists' in corrections['format_changes']:
                preferences.communication_preferences.prefers_step_by_step = True
                preferences.communication_preferences.confidence = min(1.0, preferences.communication_preferences.confidence + 0.2)
            
            if 'prefers_bullet_points' in corrections['format_changes']:
                preferences.communication_preferences.prefers_bullet_points = True
                preferences.communication_preferences.confidence = min(1.0, preferences.communication_preferences.confidence + 0.2)
            
            # Update tone preferences
            if 'prefers_friendly' in corrections['tone_indicators']:
                preferences.response_style.tone = CommunicationTone.FRIENDLY
                preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.2)
            
            elif 'prefers_professional' in corrections['tone_indicators']:
                preferences.response_style.tone = CommunicationTone.PROFESSIONAL
                preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.2)
            
            # Process additional feedback text
            if feedback_text:
                await self._process_feedback_text(preferences, feedback_text)
            
            preferences.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error applying corrections to preferences: {str(e)}")
    
    async def _process_feedback_text(self, preferences: UserPreferences, feedback_text: str) -> None:
        """Process additional feedback text for preference hints."""
        feedback_lower = feedback_text.lower()
        
        # Look for explicit style preferences
        if any(word in feedback_lower for word in ['too long', 'too verbose', 'shorter']):
            preferences.response_style.style_type = ResponseStyleType.CONCISE
            preferences.response_style.preferred_length = "short"
            preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.3)
        
        elif any(word in feedback_lower for word in ['more detail', 'elaborate', 'explain more']):
            preferences.response_style.style_type = ResponseStyleType.DETAILED
            preferences.response_style.preferred_length = "long"
            preferences.response_style.confidence = min(1.0, preferences.response_style.confidence + 0.3)
        
        # Look for communication preferences
        if any(phrase in feedback_lower for phrase in ['step by step', 'break it down', 'one by one']):
            preferences.communication_preferences.prefers_step_by_step = True
            preferences.communication_preferences.confidence = min(1.0, preferences.communication_preferences.confidence + 0.3)
        
        if any(word in feedback_lower for word in ['example', 'show me', 'demonstrate']):
            preferences.communication_preferences.prefers_code_examples = True
            preferences.communication_preferences.confidence = min(1.0, preferences.communication_preferences.confidence + 0.2)
        
        # Look for tone preferences
        if any(word in feedback_lower for word in ['too formal', 'casual', 'friendly']):
            preferences.response_style.tone = CommunicationTone.FRIENDLY
        
        elif any(word in feedback_lower for word in ['professional', 'formal', 'business']):
            preferences.response_style.tone = CommunicationTone.PROFESSIONAL
    
    async def get_preference_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user preferences for analytics."""
        try:
            preferences = await self.get_preferences(user_id)
            
            insights = {
                'user_id': user_id,
                'learning_enabled': preferences.learning_enabled,
                'confidence_scores': {
                    'response_style': preferences.response_style.confidence,
                    'communication': preferences.communication_preferences.confidence
                },
                'preferences_summary': preferences.get_preference_summary(),
                'last_updated': preferences.last_updated.isoformat() if preferences.last_updated else None,
                'total_topics': len(preferences.topic_interests),
                'top_topics': [
                    {
                        'topic': topic.topic,
                        'interest_level': topic.interest_level,
                        'frequency': topic.frequency_mentioned
                    }
                    for topic in preferences.get_top_interests(5)
                ]
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting preference insights for user {user_id}: {str(e)}")
            return {'user_id': user_id, 'error': str(e)}
    
    async def reset_preferences(self, user_id: str) -> None:
        """Reset user preferences to defaults."""
        try:
            logger.info(f"Resetting preferences for user {user_id}")
            
            # Create new default preferences
            default_preferences = UserPreferences(user_id=user_id)
            
            # Update cache
            self._preferences_cache[user_id] = default_preferences
            
            # Persist changes
            await self._persist_preferences(user_id, default_preferences)
            
            logger.info(f"Successfully reset preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting preferences for user {user_id}: {str(e)}")
            raise
    
    async def export_preferences(self, user_id: str) -> Dict[str, Any]:
        """Export user preferences for backup or migration."""
        try:
            preferences = await self.get_preferences(user_id)
            return preferences.to_dict()
            
        except Exception as e:
            logger.error(f"Error exporting preferences for user {user_id}: {str(e)}")
            raise
    
    async def import_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> None:
        """Import user preferences from backup or migration."""
        try:
            logger.info(f"Importing preferences for user {user_id}")
            
            # Validate and create preferences object
            preferences = UserPreferences.from_dict(preferences_data)
            
            # Ensure user_id matches
            preferences.user_id = user_id
            preferences.last_updated = datetime.now(timezone.utc)
            
            # Update cache
            self._preferences_cache[user_id] = preferences
            
            # Persist changes
            await self._persist_preferences(user_id, preferences)
            
            logger.info(f"Successfully imported preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error importing preferences for user {user_id}: {str(e)}")
            raise
    
    async def _adjust_response_length(self, response: str, preferred_length: str) -> str:
        """Adjust response length based on preference."""
        if preferred_length == "short" and len(response) > 300:
            return await self._make_response_concise(response)
        elif preferred_length == "long" and len(response) < 200:
            return await self._make_response_detailed(response)
        
        return response
    
    async def _add_step_by_step_formatting(self, response: str) -> str:
        """Add step-by-step formatting to the response."""
        # Look for process descriptions and format them as steps
        if any(word in response.lower() for word in ['first', 'then', 'next', 'finally', 'process']):
            # Split by sentences and periods to better identify steps
            sentences = response.replace('. ', '.\n').split('\n')
            formatted_lines = []
            step_counter = 1
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if sentence describes a step
                sentence_lower = sentence.lower()
                if any(word in sentence_lower for word in ['first', 'then', 'next', 'after', 'finally']):
                    # Remove step indicators and add numbered format
                    clean_sentence = sentence
                    step_words = ['First,', 'first,', 'Then,', 'then,', 'Next,', 'next,', 'After that,', 'after that,', 'Finally,', 'finally,']
                    for word in step_words:
                        clean_sentence = clean_sentence.replace(word, '').strip()
                    
                    # Ensure sentence ends with period
                    if not clean_sentence.endswith('.'):
                        clean_sentence += '.'
                    
                    formatted_lines.append(f"{step_counter}. {clean_sentence}")
                    step_counter += 1
                else:
                    formatted_lines.append(sentence)
            
            return ' '.join(formatted_lines)
        
        return response
    
    async def _enhance_with_code_examples(self, response: str) -> str:
        """Enhance response with code examples where appropriate."""
        # Simple implementation - add note about code examples
        if 'code' in response.lower() or 'programming' in response.lower():
            if 'example' not in response.lower():
                response += "\n\nHere's a simple example to illustrate this concept."
        
        return response
    
    async def _add_analogies(self, response: str) -> str:
        """Add analogies to help explain concepts."""
        # Simple implementation - add analogy suggestions
        if len(response) > 50 and 'like' not in response.lower() and 'similar' not in response.lower():
            response += "\n\nThink of it like a familiar concept that helps make this clearer."
        
        return response
    
    async def _add_bullet_point_formatting(self, response: str) -> str:
        """Format response with bullet points where appropriate."""
        # Look for lists and convert to bullet points
        lines = response.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append(line)
                continue
            
            # Check if line is part of a list
            if any(line.startswith(str(i) + '.') for i in range(1, 10)):
                # Convert numbered list to bullet points
                bullet_line = '• ' + line.split('.', 1)[1].strip()
                formatted_lines.append(bullet_line)
            elif line.startswith('-') or line.startswith('*'):
                # Already formatted as bullet
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    async def _make_tone_friendly(self, response: str) -> str:
        """Make the tone more friendly."""
        # Add friendly phrases
        if not any(phrase in response.lower() for phrase in ['hope', 'glad', 'happy', 'great']):
            response = "I hope this helps! " + response
        
        return response
    
    async def _make_tone_professional(self, response: str) -> str:
        """Make the tone more professional."""
        # Remove casual language and add formal structure
        professional_response = response
        
        # Replace casual greetings
        casual_to_professional = {
            'Hey': 'Hello',
            'Hi there': 'Good day',
            'Thanks!': 'Thank you.',
            'No problem': 'You are welcome'
        }
        
        for casual, professional in casual_to_professional.items():
            professional_response = professional_response.replace(casual, professional)
        
        return professional_response
    
    async def _make_tone_direct(self, response: str) -> str:
        """Make the tone more direct."""
        # Remove hedging language
        hedging_phrases = [
            'I think', 'perhaps', 'maybe', 'possibly', 'it seems like',
            'you might want to', 'you could consider'
        ]
        
        direct_response = response
        for phrase in hedging_phrases:
            direct_response = direct_response.replace(phrase, '').strip()
        
        # Clean up any double spaces
        direct_response = ' '.join(direct_response.split())
        
        return direct_response
    
    async def _make_tone_encouraging(self, response: str) -> str:
        """Make the tone more encouraging."""
        # Add encouraging phrases
        encouraging_phrases = [
            "You're on the right track!",
            "Great question!",
            "You can do this!",
            "Keep up the good work!"
        ]
        
        if not any(phrase.lower() in response.lower() for phrase in encouraging_phrases):
            response = encouraging_phrases[0] + " " + response
        
        return response