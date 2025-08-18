"""
Conversation storage repository with MongoDB integration.
Provides high-level conversation persistence and querying capabilities.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from ..models import Conversation, Message, ConversationSummary
from ..utils.database import get_database_manager
from ..utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repository for conversation storage and retrieval operations."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the conversation repository."""
        if not self._initialized:
            await self.db_manager.initialize_all()
            await self._create_indexes()
            self._initialized = True
    
    async def _create_indexes(self) -> None:
        """Create MongoDB indexes for efficient conversation queries."""
        try:
            db = self.db_manager.mongodb.database
            conversations = db.conversations
            
            # Create indexes for efficient querying
            await conversations.create_index("user_id")
            await conversations.create_index("id")
            await conversations.create_index("timestamp")
            await conversations.create_index([("user_id", 1), ("timestamp", -1)])
            await conversations.create_index([("user_id", 1), ("tags", 1)])
            
            # Text search index for conversation content
            await conversations.create_index([
                ("summary", "text"),
                ("messages.content", "text")
            ])
            
            logger.info("Conversation repository indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create conversation indexes: {e}")
            raise
    
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store a conversation with encryption for sensitive content."""
        await self._ensure_initialized()
        
        async def store_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            # Convert conversation to dict and encrypt sensitive content
            conversation_dict = conversation.model_dump()
            
            # Encrypt message content for privacy
            for message in conversation_dict.get('messages', []):
                if 'content' in message:
                    message['content'] = encrypt_sensitive_data(message['content'])
            
            # Encrypt summary if present
            if conversation_dict.get('summary'):
                conversation_dict['summary'] = encrypt_sensitive_data(conversation_dict['summary'])
            
            # Use upsert to handle updates
            result = await collection.replace_one(
                {"id": conversation.id},
                conversation_dict,
                upsert=True
            )
            
            return result.upserted_id or result.matched_count
        
        await self.db_manager.mongodb.execute_with_retry(store_operation)
        logger.info(f"Stored conversation {conversation.id} for user {conversation.user_id}")
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID with content decryption."""
        await self._ensure_initialized()
        
        async def get_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            return await collection.find_one({"id": conversation_id})
        
        doc = await self.db_manager.mongodb.execute_with_retry(get_operation)
        if not doc:
            return None
        
        try:
            # Decrypt message content
            for message in doc.get('messages', []):
                if 'content' in message:
                    message['content'] = decrypt_sensitive_data(message['content'])
            
            # Decrypt summary if present
            if doc.get('summary'):
                doc['summary'] = decrypt_sensitive_data(doc['summary'])
            
            # Remove MongoDB's _id field
            doc.pop('_id', None)
            return Conversation.model_validate(doc)
        except Exception as e:
            logger.error(f"Failed to parse conversation {conversation_id}: {e}")
            return None
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> List[Conversation]:
        """Get conversations for a user with optional filtering."""
        await self._ensure_initialized()
        
        async def get_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            # Build query filter
            query_filter = {"user_id": user_id}
            
            # Add date range filter
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query_filter["timestamp"] = date_filter
            
            # Add tags filter
            if tags:
                query_filter["tags"] = {"$in": tags}
            
            # Execute query with sorting and limit
            cursor = collection.find(query_filter).sort("timestamp", -1)
            if limit:
                cursor = cursor.limit(limit)
            
            return await cursor.to_list(length=None)
        
        docs = await self.db_manager.mongodb.execute_with_retry(get_operation)
        conversations = []
        
        for doc in docs:
            try:
                # Decrypt message content
                for message in doc.get('messages', []):
                    if 'content' in message:
                        message['content'] = decrypt_sensitive_data(message['content'])
                
                # Decrypt summary if present
                if doc.get('summary'):
                    doc['summary'] = decrypt_sensitive_data(doc['summary'])
                
                # Remove MongoDB's _id field
                doc.pop('_id', None)
                conversation = Conversation.model_validate(doc)
                conversations.append(conversation)
            except Exception as e:
                logger.error(f"Failed to parse conversation {doc.get('id', 'unknown')}: {e}")
                continue
        
        return conversations
    
    async def search_conversations(
        self, 
        user_id: str, 
        search_text: str,
        limit: int = 20
    ) -> List[Conversation]:
        """Search conversations by text content."""
        await self._ensure_initialized()
        
        async def search_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            # Use text search with user filter
            cursor = collection.find({
                "$and": [
                    {"user_id": user_id},
                    {"$text": {"$search": search_text}}
                ]
            }).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            return await cursor.to_list(length=None)
        
        docs = await self.db_manager.mongodb.execute_with_retry(search_operation)
        conversations = []
        
        for doc in docs:
            try:
                # Decrypt message content
                for message in doc.get('messages', []):
                    if 'content' in message:
                        message['content'] = decrypt_sensitive_data(message['content'])
                
                # Decrypt summary if present
                if doc.get('summary'):
                    doc['summary'] = decrypt_sensitive_data(doc['summary'])
                
                # Remove MongoDB's _id field
                doc.pop('_id', None)
                conversation = Conversation.model_validate(doc)
                conversations.append(conversation)
            except Exception as e:
                logger.error(f"Failed to parse search result {doc.get('id', 'unknown')}: {e}")
                continue
        
        return conversations
    
    async def get_recent_conversations(
        self, 
        user_id: str, 
        days: int = 7,
        limit: int = 50
    ) -> List[Conversation]:
        """Get recent conversations within the specified number of days."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.get_user_conversations(
            user_id=user_id,
            start_date=start_date,
            limit=limit
        )
    
    async def get_conversations_by_tags(
        self, 
        user_id: str, 
        tags: List[str],
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """Get conversations that contain any of the specified tags."""
        return await self.get_user_conversations(
            user_id=user_id,
            tags=tags,
            limit=limit
        )
    
    async def update_conversation_summary(
        self, 
        conversation_id: str, 
        summary: str
    ) -> bool:
        """Update the summary of a conversation."""
        await self._ensure_initialized()
        
        async def update_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            encrypted_summary = encrypt_sensitive_data(summary)
            result = await collection.update_one(
                {"id": conversation_id},
                {"$set": {"summary": encrypted_summary}}
            )
            return result.modified_count > 0
        
        success = await self.db_manager.mongodb.execute_with_retry(update_operation)
        if success:
            logger.info(f"Updated summary for conversation {conversation_id}")
        else:
            logger.warning(f"Failed to update summary for conversation {conversation_id}")
        
        return success
    
    async def add_tags_to_conversation(
        self, 
        conversation_id: str, 
        tags: List[str]
    ) -> bool:
        """Add tags to a conversation."""
        await self._ensure_initialized()
        
        async def update_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            result = await collection.update_one(
                {"id": conversation_id},
                {"$addToSet": {"tags": {"$each": tags}}}
            )
            return result.modified_count > 0
        
        success = await self.db_manager.mongodb.execute_with_retry(update_operation)
        if success:
            logger.info(f"Added tags {tags} to conversation {conversation_id}")
        
        return success
    
    async def remove_tags_from_conversation(
        self, 
        conversation_id: str, 
        tags: List[str]
    ) -> bool:
        """Remove tags from a conversation."""
        await self._ensure_initialized()
        
        async def update_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            result = await collection.update_one(
                {"id": conversation_id},
                {"$pullAll": {"tags": tags}}
            )
            return result.modified_count > 0
        
        success = await self.db_manager.mongodb.execute_with_retry(update_operation)
        if success:
            logger.info(f"Removed tags {tags} from conversation {conversation_id}")
        
        return success
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation by ID."""
        await self._ensure_initialized()
        
        async def delete_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            result = await collection.delete_one({"id": conversation_id})
            return result.deleted_count > 0
        
        success = await self.db_manager.mongodb.execute_with_retry(delete_operation)
        if success:
            logger.info(f"Deleted conversation {conversation_id}")
        else:
            logger.warning(f"Conversation {conversation_id} not found for deletion")
        
        return success
    
    async def delete_user_conversations(
        self, 
        user_id: str,
        older_than_days: Optional[int] = None
    ) -> int:
        """Delete conversations for a user, optionally only those older than specified days."""
        await self._ensure_initialized()
        
        async def delete_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            query_filter = {"user_id": user_id}
            
            if older_than_days:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                query_filter["timestamp"] = {"$lt": cutoff_date}
            
            result = await collection.delete_many(query_filter)
            return result.deleted_count
        
        deleted_count = await self.db_manager.mongodb.execute_with_retry(delete_operation)
        logger.info(f"Deleted {deleted_count} conversations for user {user_id}")
        return deleted_count
    
    async def get_conversation_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's conversations."""
        await self._ensure_initialized()
        
        async def stats_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "total_conversations": {"$sum": 1},
                    "total_messages": {"$sum": {"$size": "$messages"}},
                    "earliest_conversation": {"$min": "$timestamp"},
                    "latest_conversation": {"$max": "$timestamp"},
                    "avg_messages_per_conversation": {"$avg": {"$size": "$messages"}}
                }}
            ]
            
            result = await collection.aggregate(pipeline).to_list(length=1)
            return result[0] if result else {}
        
        stats = await self.db_manager.mongodb.execute_with_retry(stats_operation)
        
        # Add additional computed statistics
        if stats:
            if stats.get('earliest_conversation') and stats.get('latest_conversation'):
                duration = stats['latest_conversation'] - stats['earliest_conversation']
                stats['conversation_span_days'] = duration.days
            
            # Get tag statistics
            tag_stats = await self._get_tag_statistics(user_id)
            stats['tag_statistics'] = tag_stats
        
        return stats
    
    async def _get_tag_statistics(self, user_id: str) -> Dict[str, int]:
        """Get statistics about tag usage for a user."""
        async def tag_stats_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$unwind": "$tags"},
                {"$group": {
                    "_id": "$tags",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 20}  # Top 20 tags
            ]
            
            result = await collection.aggregate(pipeline).to_list(length=None)
            return {item["_id"]: item["count"] for item in result}
        
        return await self.db_manager.mongodb.execute_with_retry(tag_stats_operation)
    
    async def get_conversation_count(
        self, 
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Get the count of conversations for a user within an optional date range."""
        await self._ensure_initialized()
        
        async def count_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            query_filter = {"user_id": user_id}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query_filter["timestamp"] = date_filter
            
            return await collection.count_documents(query_filter)
        
        return await self.db_manager.mongodb.execute_with_retry(count_operation)
    
    async def health_check(self) -> bool:
        """Check if the conversation repository is healthy."""
        try:
            await self._ensure_initialized()
            return await self.db_manager.mongodb.health_check()
        except Exception as e:
            logger.error(f"Conversation repository health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close the conversation repository."""
        if self._initialized:
            await self.db_manager.close_all()
            self._initialized = False
    
    async def _ensure_initialized(self) -> None:
        """Ensure the repository is initialized."""
        if not self._initialized:
            await self.initialize()


# Global repository instance
_conversation_repository: Optional[ConversationRepository] = None


def get_conversation_repository() -> ConversationRepository:
    """Get the global conversation repository instance."""
    global _conversation_repository
    if _conversation_repository is None:
        _conversation_repository = ConversationRepository()
    return _conversation_repository


async def initialize_conversation_repository() -> None:
    """Initialize the global conversation repository."""
    repository = get_conversation_repository()
    await repository.initialize()


async def close_conversation_repository() -> None:
    """Close the global conversation repository."""
    global _conversation_repository
    if _conversation_repository:
        await _conversation_repository.close()
        _conversation_repository = None