"""
Tests for database connection utilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.memory.utils.database import (
    PostgreSQLConnection, MongoDBConnection, RedisConnection,
    DatabaseManager, DatabaseConnectionError, get_database_manager
)


class TestPostgreSQLConnection:
    """Tests for PostgreSQL connection manager."""
    
    @pytest.fixture
    def postgres_conn(self):
        return PostgreSQLConnection("postgresql://test:test@localhost:5432/test")
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, postgres_conn):
        """Test successful PostgreSQL initialization."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            # Make the mock awaitable
            async def create_pool_mock(*args, **kwargs):
                return mock_pool
            mock_create_pool.side_effect = create_pool_mock
            
            await postgres_conn.initialize()
            
            assert postgres_conn._pool == mock_pool
            mock_create_pool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, postgres_conn):
        """Test PostgreSQL initialization failure."""
        with patch('asyncpg.create_pool', side_effect=Exception("Connection failed")):
            with pytest.raises(DatabaseConnectionError):
                await postgres_conn.initialize()
    
    @pytest.mark.asyncio
    async def test_get_connection_context_manager(self, postgres_conn):
        """Test connection context manager."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value = mock_conn
        postgres_conn._pool = mock_pool
        
        async with postgres_conn.get_connection() as conn:
            assert conn == mock_conn
        
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, postgres_conn):
        """Test successful query execution with retry."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "success"
        mock_pool.acquire.return_value = mock_conn
        postgres_conn._pool = mock_pool
        
        result = await postgres_conn.execute_with_retry("SELECT 1")
        
        assert result == "success"
        mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self, postgres_conn):
        """Test query execution failure with retry."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Query failed")
        mock_pool.acquire.return_value = mock_conn
        postgres_conn._pool = mock_pool
        
        with pytest.raises(DatabaseConnectionError):
            await postgres_conn.execute_with_retry("SELECT 1", max_retries=2)
        
        assert mock_conn.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, postgres_conn):
        """Test successful health check."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value = mock_conn
        postgres_conn._pool = mock_pool
        
        result = await postgres_conn.health_check()
        
        assert result is True
        mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, postgres_conn):
        """Test health check failure."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Health check failed")
        mock_pool.acquire.return_value = mock_conn
        postgres_conn._pool = mock_pool
        
        result = await postgres_conn.health_check()
        
        assert result is False


class TestMongoDBConnection:
    """Tests for MongoDB connection manager."""
    
    @pytest.fixture
    def mongo_conn(self):
        return MongoDBConnection("mongodb://localhost:27017", "test_db")
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mongo_conn):
        """Test successful MongoDB initialization."""
        with patch('src.memory.utils.database.AsyncIOMotorClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_admin = AsyncMock()
            mock_client.admin = mock_admin
            
            # Make the admin.command method properly async
            async def mock_command(*args, **kwargs):
                return {"ok": 1}
            mock_admin.command = mock_command
            mock_client_class.return_value = mock_client
            
            await mongo_conn.initialize()
            
            assert mongo_conn._client == mock_client
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, mongo_conn):
        """Test MongoDB initialization failure."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient', side_effect=Exception("Connection failed")):
            with pytest.raises(DatabaseConnectionError):
                await mongo_conn.initialize()
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, mongo_conn):
        """Test successful operation execution with retry."""
        mock_client = AsyncMock()
        mongo_conn._client = mock_client
        mongo_conn._database = mock_client.test_db
        
        async def test_operation():
            return "success"
        
        result = await mongo_conn.execute_with_retry(test_operation)
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self, mongo_conn):
        """Test operation execution failure with retry."""
        mock_client = AsyncMock()
        mongo_conn._client = mock_client
        
        async def failing_operation():
            raise Exception("Operation failed")
        
        with pytest.raises(DatabaseConnectionError):
            await mongo_conn.execute_with_retry(failing_operation, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mongo_conn):
        """Test successful health check."""
        mock_client = AsyncMock()
        mock_client.admin.command.return_value = {"ok": 1}
        mongo_conn._client = mock_client
        
        result = await mongo_conn.health_check()
        
        assert result is True
        mock_client.admin.command.assert_called_with('ping')
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mongo_conn):
        """Test health check failure."""
        mock_client = AsyncMock()
        mock_client.admin.command.side_effect = Exception("Health check failed")
        mongo_conn._client = mock_client
        
        result = await mongo_conn.health_check()
        
        assert result is False


class TestRedisConnection:
    """Tests for Redis connection manager."""
    
    @pytest.fixture
    def redis_conn(self):
        return RedisConnection("redis://localhost:6379/0")
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, redis_conn):
        """Test successful Redis initialization."""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_pool_class.from_url.return_value = mock_pool
            
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis_class.return_value = mock_client
            
            await redis_conn.initialize()
            
            assert redis_conn._client == mock_client
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, redis_conn):
        """Test Redis initialization failure."""
        with patch('redis.asyncio.ConnectionPool.from_url', side_effect=Exception("Connection failed")):
            with pytest.raises(DatabaseConnectionError):
                await redis_conn.initialize()
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, redis_conn):
        """Test successful operation execution with retry."""
        mock_client = AsyncMock()
        redis_conn._client = mock_client
        
        async def test_operation():
            return "success"
        
        result = await redis_conn.execute_with_retry(test_operation)
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self, redis_conn):
        """Test operation execution failure with retry."""
        mock_client = AsyncMock()
        redis_conn._client = mock_client
        
        async def failing_operation():
            raise Exception("Operation failed")
        
        with pytest.raises(DatabaseConnectionError):
            await redis_conn.execute_with_retry(failing_operation, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, redis_conn):
        """Test successful health check."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        redis_conn._client = mock_client
        
        result = await redis_conn.health_check()
        
        assert result is True
        mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, redis_conn):
        """Test health check failure."""
        mock_client = AsyncMock()
        mock_client.ping.side_effect = Exception("Health check failed")
        redis_conn._client = mock_client
        
        result = await redis_conn.health_check()
        
        assert result is False


class TestDatabaseManager:
    """Tests for database manager."""
    
    @pytest.fixture
    def db_manager(self):
        with patch('src.memory.utils.database.get_memory_config') as mock_config:
            mock_config.return_value.postgres_url = "postgresql://test:test@localhost:5432/test"
            mock_config.return_value.mongodb_url = "mongodb://localhost:27017/test"
            mock_config.return_value.redis_url = "redis://localhost:6379/0"
            return DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_initialize_all_success(self, db_manager):
        """Test successful initialization of all databases."""
        with patch.object(db_manager.postgres, 'initialize') as mock_pg_init, \
             patch.object(db_manager.mongodb, 'initialize') as mock_mongo_init, \
             patch.object(db_manager.redis, 'initialize') as mock_redis_init:
            
            await db_manager.initialize_all()
            
            assert db_manager._initialized is True
            mock_pg_init.assert_called_once()
            mock_mongo_init.assert_called_once()
            mock_redis_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_all_failure(self, db_manager):
        """Test initialization failure handling."""
        with patch.object(db_manager.postgres, 'initialize', side_effect=Exception("Init failed")), \
             patch.object(db_manager, 'close_all') as mock_close:
            
            with pytest.raises(Exception):
                await db_manager.initialize_all()
            
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, db_manager):
        """Test health check for all databases."""
        with patch.object(db_manager.postgres, 'health_check', return_value=True), \
             patch.object(db_manager.mongodb, 'health_check', return_value=True), \
             patch.object(db_manager.redis, 'health_check', return_value=False):
            
            results = await db_manager.health_check_all()
            
            assert results == {
                "postgres": True,
                "mongodb": True,
                "redis": False
            }
    
    @pytest.mark.asyncio
    async def test_close_all(self, db_manager):
        """Test closing all database connections."""
        with patch.object(db_manager.postgres, 'close') as mock_pg_close, \
             patch.object(db_manager.mongodb, 'close') as mock_mongo_close, \
             patch.object(db_manager.redis, 'close') as mock_redis_close:
            
            db_manager._initialized = True
            await db_manager.close_all()
            
            assert db_manager._initialized is False
            mock_pg_close.assert_called_once()
            mock_mongo_close.assert_called_once()
            mock_redis_close.assert_called_once()


def test_get_database_manager():
    """Test getting the global database manager instance."""
    manager1 = get_database_manager()
    manager2 = get_database_manager()
    
    assert manager1 is manager2  # Should return the same instance