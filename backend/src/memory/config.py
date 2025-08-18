"""
Configuration settings for the conversational memory system.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class MemoryConfig(BaseSettings):
    """Configuration for the memory system."""
    
    # Database settings
    postgres_url: str = Field(
        default="postgresql://localhost:5432/memory_db",
        env="POSTGRES_URL"
    )
    mongodb_url: str = Field(
        default="mongodb://localhost:27017/memory_db",
        env="MONGODB_URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Vector database settings
    vector_db_url: Optional[str] = Field(
        default=None,
        env="VECTOR_DB_URL"
    )
    
    # Memory system settings
    max_context_messages: int = Field(default=50, env="MAX_CONTEXT_MESSAGES")
    context_retention_days: int = Field(default=90, env="CONTEXT_RETENTION_DAYS")
    max_conversation_length: int = Field(default=1000, env="MAX_CONVERSATION_LENGTH")
    
    # Search settings
    search_results_limit: int = Field(default=20, env="SEARCH_RESULTS_LIMIT")
    semantic_search_enabled: bool = Field(default=True, env="SEMANTIC_SEARCH_ENABLED")
    
    # Privacy settings
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    audit_logging_enabled: bool = Field(default=True, env="AUDIT_LOGGING_ENABLED")
    
    # Performance settings
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    
    # Feature flags
    preference_learning_enabled: bool = Field(default=True, env="PREFERENCE_LEARNING_ENABLED")
    conversation_summarization_enabled: bool = Field(default=True, env="CONVERSATION_SUMMARIZATION_ENABLED")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
memory_config = MemoryConfig()


def get_memory_config() -> MemoryConfig:
    """Get the memory system configuration."""
    return memory_config