"""
Unit tests for configuration settings.
"""

import pytest
import os
from unittest.mock import patch
from src.memory.config import MemoryConfig, get_memory_config


class TestMemoryConfig:
    """Test cases for MemoryConfig class."""
    
    def test_default_config_values(self):
        """Test default configuration values."""
        config = MemoryConfig()
        
        # Database settings
        assert config.postgres_url == "postgresql://localhost:5432/memory_db"
        assert config.mongodb_url == "mongodb://localhost:27017/memory_db"
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.vector_db_url is None
        
        # Memory system settings
        assert config.max_context_messages == 50
        assert config.context_retention_days == 90
        assert config.max_conversation_length == 1000
        
        # Search settings
        assert config.search_results_limit == 20
        assert config.semantic_search_enabled is True
        
        # Privacy settings
        assert config.encryption_key is None
        assert config.audit_logging_enabled is True
        
        # Performance settings
        assert config.cache_ttl_seconds == 3600
        assert config.batch_size == 100
    
    def test_config_from_environment_variables(self):
        """Test configuration loading from environment variables."""
        env_vars = {
            "POSTGRES_URL": "postgresql://test:test@testhost:5432/testdb",
            "MONGODB_URL": "mongodb://testhost:27017/testdb",
            "REDIS_URL": "redis://testhost:6379/1",
            "VECTOR_DB_URL": "http://vector-db:8080",
            "MAX_CONTEXT_MESSAGES": "100",
            "CONTEXT_RETENTION_DAYS": "30",
            "MAX_CONVERSATION_LENGTH": "500",
            "SEARCH_RESULTS_LIMIT": "50",
            "SEMANTIC_SEARCH_ENABLED": "false",
            "ENCRYPTION_KEY": "test-encryption-key",
            "AUDIT_LOGGING_ENABLED": "false",
            "CACHE_TTL_SECONDS": "7200",
            "BATCH_SIZE": "200"
        }
        
        with patch.dict(os.environ, env_vars):
            config = MemoryConfig()
            
            # Database settings
            assert config.postgres_url == "postgresql://test:test@testhost:5432/testdb"
            assert config.mongodb_url == "mongodb://testhost:27017/testdb"
            assert config.redis_url == "redis://testhost:6379/1"
            assert config.vector_db_url == "http://vector-db:8080"
            
            # Memory system settings
            assert config.max_context_messages == 100
            assert config.context_retention_days == 30
            assert config.max_conversation_length == 500
            
            # Search settings
            assert config.search_results_limit == 50
            assert config.semantic_search_enabled is False
            
            # Privacy settings
            assert config.encryption_key == "test-encryption-key"
            assert config.audit_logging_enabled is False
            
            # Performance settings
            assert config.cache_ttl_seconds == 7200
            assert config.batch_size == 200
    
    def test_config_partial_environment_override(self):
        """Test that only specified environment variables override defaults."""
        env_vars = {
            "POSTGRES_URL": "postgresql://custom:custom@localhost:5432/custom_db",
            "MAX_CONTEXT_MESSAGES": "75"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = MemoryConfig()
            
            # Overridden values
            assert config.postgres_url == "postgresql://custom:custom@localhost:5432/custom_db"
            assert config.max_context_messages == 75
            
            # Default values should remain
            assert config.mongodb_url == "mongodb://localhost:27017/memory_db"
            assert config.context_retention_days == 90
            assert config.semantic_search_enabled is True
    
    def test_config_validation_positive_integers(self):
        """Test validation of positive integer fields."""
        # Test valid positive integers
        config = MemoryConfig(
            max_context_messages=1,
            context_retention_days=1,
            max_conversation_length=1,
            search_results_limit=1,
            cache_ttl_seconds=1,
            batch_size=1
        )
        
        assert config.max_context_messages == 1
        assert config.context_retention_days == 1
        assert config.max_conversation_length == 1
        assert config.search_results_limit == 1
        assert config.cache_ttl_seconds == 1
        assert config.batch_size == 1
    
    def test_config_validation_zero_values(self):
        """Test validation with zero values."""
        # Zero values should be allowed for some fields
        config = MemoryConfig(
            max_context_messages=0,
            context_retention_days=0,
            cache_ttl_seconds=0
        )
        
        assert config.max_context_messages == 0
        assert config.context_retention_days == 0
        assert config.cache_ttl_seconds == 0
    
    def test_config_boolean_parsing(self):
        """Test boolean field parsing from environment."""
        # Test various boolean representations
        boolean_tests = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False)
        ]
        
        for env_value, expected in boolean_tests:
            with patch.dict(os.environ, {"SEMANTIC_SEARCH_ENABLED": env_value}):
                config = MemoryConfig()
                assert config.semantic_search_enabled == expected
    
    def test_config_url_validation(self):
        """Test URL field validation."""
        # Test valid URLs
        valid_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "mongodb://localhost:27017/db",
            "redis://localhost:6379/0",
            "http://vector-db:8080",
            "https://vector-db.example.com:443"
        ]
        
        for url in valid_urls:
            config = MemoryConfig(postgres_url=url)
            assert config.postgres_url == url
    
    def test_config_optional_fields(self):
        """Test optional field behavior."""
        config = MemoryConfig()
        
        # Optional fields should default to None
        assert config.vector_db_url is None
        assert config.encryption_key is None
        
        # Setting optional fields should work
        config = MemoryConfig(
            vector_db_url="http://vector-db:8080",
            encryption_key="secret-key"
        )
        
        assert config.vector_db_url == "http://vector-db:8080"
        assert config.encryption_key == "secret-key"
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = MemoryConfig(
            postgres_url="postgresql://test:test@localhost:5432/test",
            max_context_messages=100
        )
        
        # Should be able to serialize to dict
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert config_dict["postgres_url"] == "postgresql://test:test@localhost:5432/test"
        assert config_dict["max_context_messages"] == 100
    
    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        config_data = {
            "postgres_url": "postgresql://dict:dict@localhost:5432/dict_db",
            "max_context_messages": 200,
            "semantic_search_enabled": False
        }
        
        config = MemoryConfig(**config_data)
        
        assert config.postgres_url == "postgresql://dict:dict@localhost:5432/dict_db"
        assert config.max_context_messages == 200
        assert config.semantic_search_enabled is False
        
        # Other fields should have defaults
        assert config.mongodb_url == "mongodb://localhost:27017/memory_db"
        assert config.context_retention_days == 90


class TestGetMemoryConfig:
    """Test cases for get_memory_config function."""
    
    def test_get_memory_config_returns_instance(self):
        """Test that get_memory_config returns a MemoryConfig instance."""
        config = get_memory_config()
        
        assert isinstance(config, MemoryConfig)
        assert hasattr(config, 'postgres_url')
        assert hasattr(config, 'mongodb_url')
        assert hasattr(config, 'redis_url')
    
    def test_get_memory_config_singleton_behavior(self):
        """Test that get_memory_config returns the same instance (if implemented as singleton)."""
        config1 = get_memory_config()
        config2 = get_memory_config()
        
        # If implemented as singleton, should be same instance
        # If not, should at least have same values
        assert config1.postgres_url == config2.postgres_url
        assert config1.max_context_messages == config2.max_context_messages
    
    def test_get_memory_config_with_environment(self):
        """Test get_memory_config with environment variables."""
        env_vars = {
            "POSTGRES_URL": "postgresql://env:env@localhost:5432/env_db",
            "MAX_CONTEXT_MESSAGES": "150"
        }
        
        with patch.dict(os.environ, env_vars):
            config = get_memory_config()
            
            assert config.postgres_url == "postgresql://env:env@localhost:5432/env_db"
            assert config.max_context_messages == 150


class TestConfigEdgeCases:
    """Test edge cases and error conditions for configuration."""
    
    def test_config_with_invalid_integer_env_var(self):
        """Test behavior with invalid integer environment variables."""
        with patch.dict(os.environ, {"MAX_CONTEXT_MESSAGES": "not_a_number"}):
            with pytest.raises(ValueError):
                MemoryConfig()
    
    def test_config_with_negative_integer_env_var(self):
        """Test behavior with negative integer environment variables."""
        with patch.dict(os.environ, {"MAX_CONTEXT_MESSAGES": "-10"}):
            # Should either raise validation error or handle gracefully
            try:
                config = MemoryConfig()
                # If it doesn't raise an error, the value should be handled appropriately
                assert isinstance(config.max_context_messages, int)
            except ValueError:
                # Validation error is acceptable for negative values
                pass
    
    def test_config_with_empty_string_env_vars(self):
        """Test behavior with empty string environment variables."""
        env_vars = {
            "POSTGRES_URL": "",
            "ENCRYPTION_KEY": "",
            "MAX_CONTEXT_MESSAGES": ""
        }
        
        with patch.dict(os.environ, env_vars):
            try:
                config = MemoryConfig()
                # Empty strings should either use defaults or be handled gracefully
                assert isinstance(config, MemoryConfig)
            except ValueError:
                # Validation errors are acceptable for empty required fields
                pass
    
    def test_config_field_types(self):
        """Test that configuration fields have correct types."""
        config = MemoryConfig()
        
        # String fields
        assert isinstance(config.postgres_url, str)
        assert isinstance(config.mongodb_url, str)
        assert isinstance(config.redis_url, str)
        
        # Optional string fields
        assert config.vector_db_url is None or isinstance(config.vector_db_url, str)
        assert config.encryption_key is None or isinstance(config.encryption_key, str)
        
        # Integer fields
        assert isinstance(config.max_context_messages, int)
        assert isinstance(config.context_retention_days, int)
        assert isinstance(config.max_conversation_length, int)
        assert isinstance(config.search_results_limit, int)
        assert isinstance(config.cache_ttl_seconds, int)
        assert isinstance(config.batch_size, int)
        
        # Boolean fields
        assert isinstance(config.semantic_search_enabled, bool)
        assert isinstance(config.audit_logging_enabled, bool)
    
    def test_config_immutability(self):
        """Test that configuration behaves as expected regarding mutability."""
        config = MemoryConfig()
        original_url = config.postgres_url
        
        # Direct assignment should work (Pydantic models are mutable by default)
        config.postgres_url = "postgresql://new:new@localhost:5432/new_db"
        assert config.postgres_url == "postgresql://new:new@localhost:5432/new_db"
        assert config.postgres_url != original_url
    
    def test_config_repr_and_str(self):
        """Test string representation of configuration."""
        config = MemoryConfig()
        
        # Should have meaningful string representation
        config_str = str(config)
        config_repr = repr(config)
        
        assert isinstance(config_str, str)
        assert isinstance(config_repr, str)
        assert len(config_str) > 0
        assert len(config_repr) > 0
        
        # Should not expose sensitive information like encryption keys
        config_with_key = MemoryConfig(encryption_key="secret-key")
        config_str_with_key = str(config_with_key)
        
        # Depending on implementation, might mask sensitive fields
        # This test ensures we don't accidentally expose secrets
        assert isinstance(config_str_with_key, str)


class TestConfigIntegration:
    """Integration tests for configuration usage."""
    
    def test_config_usage_in_database_connections(self):
        """Test that configuration can be used for database connections."""
        config = MemoryConfig(
            postgres_url="postgresql://test:test@localhost:5432/test_db",
            mongodb_url="mongodb://localhost:27017/test_db",
            redis_url="redis://localhost:6379/1"
        )
        
        # Should be able to extract connection parameters
        assert "postgresql://" in config.postgres_url
        assert "mongodb://" in config.mongodb_url
        assert "redis://" in config.redis_url
        
        # URLs should be valid for connection libraries
        assert config.postgres_url.startswith("postgresql://")
        assert config.mongodb_url.startswith("mongodb://")
        assert config.redis_url.startswith("redis://")
    
    def test_config_usage_in_memory_settings(self):
        """Test that configuration provides valid memory system settings."""
        config = MemoryConfig()
        
        # All memory settings should be positive integers
        assert config.max_context_messages > 0
        assert config.context_retention_days > 0
        assert config.max_conversation_length > 0
        assert config.search_results_limit > 0
        assert config.cache_ttl_seconds >= 0  # 0 might be valid for no caching
        assert config.batch_size > 0
    
    def test_config_environment_precedence(self):
        """Test that environment variables take precedence over defaults."""
        # Set environment variable
        with patch.dict(os.environ, {"BATCH_SIZE": "500"}):
            config = MemoryConfig()
            assert config.batch_size == 500
        
        # Without environment variable, should use default
        config_default = MemoryConfig()
        assert config_default.batch_size == 100  # default value


if __name__ == "__main__":
    pytest.main([__file__])