"""
Storage backend implementations for different database systems.
Provides concrete implementations of the storage abstraction layer.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from ..interfaces.storage_layer import StorageLayerInterface
from ..models import (
    Conversation, ConversationSummary, UserPreferences, 
    PrivacySettings, SearchResult
)
from ..utils.database import get_database_manager
from ..utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data

logger = logging.getLogger(__name__)


class BaseStorageBackend(StorageLayerInterface):
    """Base storage backend with common functionality."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        await self.db_manager.initialize_all()
    
    async def close(self) -> None:
        """Close the storage backend."""
        await self.db_manager.close_all()
    
    def _encrypt_if_sensitive(self, data: str, is_sensitive: bool = False) -> str:
        """Encrypt data if it's marked as sensitive."""
        if is_sensitive:
            return encrypt_sensitive_data(data)
        return data
    
    def _decrypt_if_sensitive(self, data: str, is_sensitive: bool = False) -> str:
        """Decrypt data if it's marked as sensitive."""
        if is_sensitive:
            return decrypt_sensitive_data(data)
        return data


class PostgreSQLStorageBackend(BaseStorageBackend):
    """PostgreSQL storage backend implementation."""
    
    async def initialize(self) -> None:
        """Initialize PostgreSQL storage backend."""
        await super().initialize()
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        create_tables_sql = """
        -- User preferences table
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id VARCHAR(255) PRIMARY KEY,
            preferences JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Privacy settings table
        CREATE TABLE IF NOT EXISTS privacy_settings (
            user_id VARCHAR(255) PRIMARY KEY,
            settings JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Conversation summaries table
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            conversation_id VARCHAR(255) NOT NULL,
            summary TEXT NOT NULL,
            key_topics TEXT[],
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_id ON conversation_summaries(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conversation_id ON conversation_summaries(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_conversation_summaries_created_at ON conversation_summaries(created_at);
        """
        
        try:
            await self.db_manager.postgres.execute_with_retry(create_tables_sql)
            logger.info("PostgreSQL tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            raise
    
    # User preferences
    async def store_user_preferences(self, preferences: UserPreferences) -> None:
        """Store user preferences in PostgreSQL."""
        query = """
        INSERT INTO user_preferences (user_id, preferences, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (user_id) 
        DO UPDATE SET preferences = $2, updated_at = NOW()
        """
        
        preferences_json = preferences.model_dump_json()
        encrypted_prefs = self._encrypt_if_sensitive(preferences_json, True)
        
        await self.db_manager.postgres.execute_with_retry(
            query, preferences.user_id, encrypted_prefs
        )
        logger.info(f"Stored user preferences for user {preferences.user_id}")
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences from PostgreSQL."""
        query = "SELECT preferences FROM user_preferences WHERE user_id = $1"
        
        rows = await self.db_manager.postgres.fetch_with_retry(query, user_id)
        if not rows:
            return None
        
        encrypted_prefs = rows[0]['preferences']
        decrypted_prefs = self._decrypt_if_sensitive(encrypted_prefs, True)
        
        try:
            return UserPreferences.model_validate_json(decrypted_prefs)
        except Exception as e:
            logger.error(f"Failed to parse user preferences for {user_id}: {e}")
            return None
    
    # Privacy settings
    async def store_privacy_settings(self, settings: PrivacySettings) -> None:
        """Store privacy settings in PostgreSQL."""
        query = """
        INSERT INTO privacy_settings (user_id, settings, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (user_id) 
        DO UPDATE SET settings = $2, updated_at = NOW()
        """
        
        settings_json = settings.model_dump_json()
        encrypted_settings = self._encrypt_if_sensitive(settings_json, True)
        
        await self.db_manager.postgres.execute_with_retry(
            query, settings.user_id, encrypted_settings
        )
        logger.info(f"Stored privacy settings for user {settings.user_id}")
    
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings from PostgreSQL."""
        query = "SELECT settings FROM privacy_settings WHERE user_id = $1"
        
        rows = await self.db_manager.postgres.fetch_with_retry(query, user_id)
        if not rows:
            return None
        
        encrypted_settings = rows[0]['settings']
        decrypted_settings = self._decrypt_if_sensitive(encrypted_settings, True)
        
        try:
            return PrivacySettings.model_validate_json(decrypted_settings)
        except Exception as e:
            logger.error(f"Failed to parse privacy settings for {user_id}: {e}")
            return None
    
    # Conversation summaries
    async def store_conversation_summary(self, summary: ConversationSummary) -> None:
        """Store conversation summary in PostgreSQL."""
        query = """
        INSERT INTO conversation_summaries (id, user_id, conversation_id, summary, key_topics, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (id) 
        DO UPDATE SET summary = $4, key_topics = $5, updated_at = NOW()
        """
        
        # Generate a unique ID for the summary since ConversationSummary doesn't have one
        summary_id = f"{summary.conversation_id}_{int(summary.timestamp.timestamp())}"
        encrypted_summary = self._encrypt_if_sensitive(summary.summary_text, True)
        
        await self.db_manager.postgres.execute_with_retry(
            query, summary_id, "unknown_user", summary.conversation_id,
            encrypted_summary, summary.key_topics
        )
        logger.info(f"Stored conversation summary {summary_id}")
    
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries from PostgreSQL."""
        query = """
        SELECT id, user_id, conversation_id, summary, key_topics, created_at, updated_at
        FROM conversation_summaries 
        WHERE user_id = $1 
        ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = await self.db_manager.postgres.fetch_with_retry(query, user_id)
        summaries = []
        
        for row in rows:
            try:
                decrypted_summary = self._decrypt_if_sensitive(row['summary'], True)
                summary = ConversationSummary(
                    conversation_id=row['conversation_id'],
                    timestamp=row['created_at'],
                    summary_text=decrypted_summary,
                    key_topics=row['key_topics'],
                    importance_score=0.0,
                    message_count=0
                )
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to parse conversation summary {row['id']}: {e}")
                continue
        
        return summaries
    
    # Data management
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all user data from PostgreSQL."""
        queries = [
            "DELETE FROM user_preferences WHERE user_id = $1",
            "DELETE FROM privacy_settings WHERE user_id = $1",
            "DELETE FROM conversation_summaries WHERE user_id = $1"
        ]
        
        for query in queries:
            await self.db_manager.postgres.execute_with_retry(query, user_id)
        
        logger.info(f"Deleted all PostgreSQL data for user {user_id}")
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user data from PostgreSQL."""
        queries = {
            "preferences_count": "SELECT COUNT(*) FROM user_preferences WHERE user_id = $1",
            "privacy_settings_count": "SELECT COUNT(*) FROM privacy_settings WHERE user_id = $1",
            "conversation_summaries_count": "SELECT COUNT(*) FROM conversation_summaries WHERE user_id = $1"
        }
        
        summary = {}
        for key, query in queries.items():
            rows = await self.db_manager.postgres.fetch_with_retry(query, user_id)
            summary[key] = rows[0]['count'] if rows else 0
        
        return summary
    
    async def health_check(self) -> bool:
        """Check PostgreSQL health."""
        return await self.db_manager.postgres.health_check()
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data from PostgreSQL."""
        # This would implement retention policies
        # For now, just log that cleanup was called
        logger.info("PostgreSQL cleanup_expired_data called")
    
    # Conversation storage (placeholder - will be implemented in MongoDB backend)
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store conversation - not implemented in PostgreSQL backend."""
        raise NotImplementedError("Conversation storage is handled by MongoDB backend")
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation - not implemented in PostgreSQL backend."""
        raise NotImplementedError("Conversation retrieval is handled by MongoDB backend")
    
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get user conversations - not implemented in PostgreSQL backend."""
        raise NotImplementedError("Conversation retrieval is handled by MongoDB backend")
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete conversation - not implemented in PostgreSQL backend."""
        raise NotImplementedError("Conversation deletion is handled by MongoDB backend")


class MongoDBStorageBackend(BaseStorageBackend):
    """MongoDB storage backend implementation."""
    
    async def initialize(self) -> None:
        """Initialize MongoDB storage backend."""
        await super().initialize()
        await self._create_indexes()
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes for better performance."""
        try:
            db = self.db_manager.mongodb.database
            
            # Conversations collection indexes
            conversations = db.conversations
            await conversations.create_index("user_id")
            await conversations.create_index("conversation_id")
            await conversations.create_index("created_at")
            await conversations.create_index([("user_id", 1), ("created_at", -1)])
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            raise
    
    # Conversation storage
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store conversation in MongoDB."""
        async def store_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            # Convert conversation to dict and encrypt sensitive content
            conversation_dict = conversation.model_dump()
            
            # Encrypt message content
            for message in conversation_dict.get('messages', []):
                if 'content' in message:
                    message['content'] = self._encrypt_if_sensitive(message['content'], True)
            
            # Use upsert to handle updates
            await collection.replace_one(
                {"id": conversation.id},
                conversation_dict,
                upsert=True
            )
        
        await self.db_manager.mongodb.execute_with_retry(store_operation)
        logger.info(f"Stored conversation {conversation.id}")
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve conversation from MongoDB."""
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
                    message['content'] = self._decrypt_if_sensitive(message['content'], True)
            
            # Remove MongoDB's _id field
            doc.pop('_id', None)
            return Conversation.model_validate(doc)
        except Exception as e:
            logger.error(f"Failed to parse conversation {conversation_id}: {e}")
            return None
    
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get conversations for a user from MongoDB."""
        async def get_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            
            # Build query filter
            query_filter = {"user_id": user_id}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query_filter["timestamp"] = date_filter
            
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
                        message['content'] = self._decrypt_if_sensitive(message['content'], True)
                
                # Remove MongoDB's _id field
                doc.pop('_id', None)
                conversation = Conversation.model_validate(doc)
                conversations.append(conversation)
            except Exception as e:
                logger.error(f"Failed to parse conversation {doc.get('id', 'unknown')}: {e}")
                continue
        
        return conversations
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete conversation from MongoDB."""
        async def delete_operation():
            db = self.db_manager.mongodb.database
            collection = db.conversations
            result = await collection.delete_one({"id": conversation_id})
            return result.deleted_count
        
        deleted_count = await self.db_manager.mongodb.execute_with_retry(delete_operation)
        if deleted_count > 0:
            logger.info(f"Deleted conversation {conversation_id}")
        else:
            logger.warning(f"Conversation {conversation_id} not found for deletion")
    
    # Data management
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all user data from MongoDB."""
        async def delete_operation():
            db = self.db_manager.mongodb.database
            conversations = db.conversations
            result = await conversations.delete_many({"user_id": user_id})
            return result.deleted_count
        
        deleted_count = await self.db_manager.mongodb.execute_with_retry(delete_operation)
        logger.info(f"Deleted {deleted_count} conversations for user {user_id}")
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user data from MongoDB."""
        async def summary_operation():
            db = self.db_manager.mongodb.database
            conversations = db.conversations
            
            # Count conversations
            conversation_count = await conversations.count_documents({"user_id": user_id})
            
            # Get date range
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "earliest": {"$min": "$timestamp"},
                    "latest": {"$max": "$timestamp"}
                }}
            ]
            
            date_range = await conversations.aggregate(pipeline).to_list(length=1)
            
            return {
                "conversation_count": conversation_count,
                "earliest_conversation": date_range[0]["earliest"] if date_range else None,
                "latest_conversation": date_range[0]["latest"] if date_range else None
            }
        
        return await self.db_manager.mongodb.execute_with_retry(summary_operation)
    
    async def health_check(self) -> bool:
        """Check MongoDB health."""
        return await self.db_manager.mongodb.health_check()
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data from MongoDB."""
        # This would implement retention policies
        # For now, just log that cleanup was called
        logger.info("MongoDB cleanup_expired_data called")
    
    # Methods not implemented in MongoDB backend (handled by PostgreSQL)
    async def store_user_preferences(self, preferences: UserPreferences) -> None:
        """Store user preferences - not implemented in MongoDB backend."""
        raise NotImplementedError("User preferences storage is handled by PostgreSQL backend")
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences - not implemented in MongoDB backend."""
        raise NotImplementedError("User preferences retrieval is handled by PostgreSQL backend")
    
    async def store_privacy_settings(self, settings: PrivacySettings) -> None:
        """Store privacy settings - not implemented in MongoDB backend."""
        raise NotImplementedError("Privacy settings storage is handled by PostgreSQL backend")
    
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings - not implemented in MongoDB backend."""
        raise NotImplementedError("Privacy settings retrieval is handled by PostgreSQL backend")
    
    async def store_conversation_summary(self, summary: ConversationSummary) -> None:
        """Store conversation summary - not implemented in MongoDB backend."""
        raise NotImplementedError("Conversation summary storage is handled by PostgreSQL backend")
    
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries - not implemented in MongoDB backend."""
        raise NotImplementedError("Conversation summary retrieval is handled by PostgreSQL backend")


class HybridStorageBackend(BaseStorageBackend):
    """Hybrid storage backend that combines PostgreSQL and MongoDB."""
    
    def __init__(self):
        super().__init__()
        self.postgres_backend = PostgreSQLStorageBackend()
        self.mongodb_backend = MongoDBStorageBackend()
    
    async def initialize(self) -> None:
        """Initialize both storage backends."""
        await self.postgres_backend.initialize()
        await self.mongodb_backend.initialize()
    
    async def close(self) -> None:
        """Close both storage backends."""
        await self.postgres_backend.close()
        await self.mongodb_backend.close()
    
    # Conversation storage (MongoDB)
    async def store_conversation(self, conversation: Conversation) -> None:
        """Store conversation using MongoDB backend."""
        return await self.mongodb_backend.store_conversation(conversation)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation using MongoDB backend."""
        return await self.mongodb_backend.get_conversation(conversation_id)
    
    async def get_user_conversations(self, user_id: str, limit: Optional[int] = None, 
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Conversation]:
        """Get user conversations using MongoDB backend."""
        return await self.mongodb_backend.get_user_conversations(user_id, limit, start_date, end_date)
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete conversation using MongoDB backend."""
        return await self.mongodb_backend.delete_conversation(conversation_id)
    
    # User preferences and settings (PostgreSQL)
    async def store_user_preferences(self, preferences: UserPreferences) -> None:
        """Store user preferences using PostgreSQL backend."""
        return await self.postgres_backend.store_user_preferences(preferences)
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences using PostgreSQL backend."""
        return await self.postgres_backend.get_user_preferences(user_id)
    
    async def store_privacy_settings(self, settings: PrivacySettings) -> None:
        """Store privacy settings using PostgreSQL backend."""
        return await self.postgres_backend.store_privacy_settings(settings)
    
    async def get_privacy_settings(self, user_id: str) -> Optional[PrivacySettings]:
        """Get privacy settings using PostgreSQL backend."""
        return await self.postgres_backend.get_privacy_settings(user_id)
    
    async def store_conversation_summary(self, summary: ConversationSummary) -> None:
        """Store conversation summary using PostgreSQL backend."""
        return await self.postgres_backend.store_conversation_summary(summary)
    
    async def get_conversation_summaries(self, user_id: str, limit: Optional[int] = None) -> List[ConversationSummary]:
        """Get conversation summaries using PostgreSQL backend."""
        return await self.postgres_backend.get_conversation_summaries(user_id, limit)
    
    # Data management (both backends)
    async def delete_all_user_data(self, user_id: str) -> None:
        """Delete all user data from both backends."""
        await self.postgres_backend.delete_all_user_data(user_id)
        await self.mongodb_backend.delete_all_user_data(user_id)
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user data from both backends."""
        postgres_summary = await self.postgres_backend.get_user_data_summary(user_id)
        mongodb_summary = await self.mongodb_backend.get_user_data_summary(user_id)
        
        return {
            "postgres": postgres_summary,
            "mongodb": mongodb_summary
        }
    
    async def health_check(self) -> bool:
        """Check health of both backends."""
        postgres_healthy = await self.postgres_backend.health_check()
        mongodb_healthy = await self.mongodb_backend.health_check()
        return postgres_healthy and mongodb_healthy
    
    async def cleanup_expired_data(self) -> None:
        """Clean up expired data from both backends."""
        await self.postgres_backend.cleanup_expired_data()
        await self.mongodb_backend.cleanup_expired_data()