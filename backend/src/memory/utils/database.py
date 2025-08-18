"""
Database connection utilities for PostgreSQL, MongoDB, and Redis.
Provides connection management, pooling, and retry logic.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from ..config import get_memory_config

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class PostgreSQLConnection:
    """PostgreSQL connection manager with pooling and retry logic."""
    
    def __init__(self, connection_url: str, min_size: int = 5, max_size: int = 20):
        self.connection_url = connection_url
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return
            
        async with self._lock:
            if self._pool is not None:
                return
                
            try:
                self._pool = await asyncpg.create_pool(
                    self.connection_url,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=30,
                    server_settings={
                        'jit': 'off'  # Disable JIT for better performance on small queries
                    }
                )
                logger.info("PostgreSQL connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL pool: {e}")
                raise DatabaseConnectionError(f"PostgreSQL connection failed: {e}")
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if not self._pool:
            await self.initialize()
        
        connection = None
        try:
            connection = await self._pool.acquire()
            yield connection
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            raise DatabaseConnectionError(f"PostgreSQL operation failed: {e}")
        finally:
            if connection:
                await self._pool.release(connection)
    
    async def execute_with_retry(self, query: str, *args, max_retries: int = 3) -> Any:
        """Execute a query with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    return await conn.execute(query, *args)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"PostgreSQL query failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"PostgreSQL query failed after {max_retries} attempts: {e}")
        
        raise DatabaseConnectionError(f"PostgreSQL query failed after {max_retries} attempts: {last_error}")
    
    async def fetch_with_retry(self, query: str, *args, max_retries: int = 3) -> list:
        """Fetch query results with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    return await conn.fetch(query, *args)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"PostgreSQL fetch failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"PostgreSQL fetch failed after {max_retries} attempts: {e}")
        
        raise DatabaseConnectionError(f"PostgreSQL fetch failed after {max_retries} attempts: {last_error}")
    
    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False


class MongoDBConnection:
    """MongoDB connection manager with retry logic."""
    
    def __init__(self, connection_url: str, database_name: str = "memory_db"):
        self.connection_url = connection_url
        self.database_name = database_name
        self._client: Optional[AsyncIOMotorClient] = None
        self._database = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the MongoDB connection."""
        if self._client is not None:
            return
            
        async with self._lock:
            if self._client is not None:
                return
                
            try:
                self._client = AsyncIOMotorClient(
                    self.connection_url,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                    maxPoolSize=50,
                    minPoolSize=5
                )
                
                # Test the connection
                await self._client.admin.command('ping')
                self._database = self._client[self.database_name]
                logger.info("MongoDB connection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB connection: {e}")
                raise DatabaseConnectionError(f"MongoDB connection failed: {e}")
    
    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")
    
    @property
    def database(self):
        """Get the database instance."""
        if not self._database:
            raise DatabaseConnectionError("MongoDB not initialized")
        return self._database
    
    async def execute_with_retry(self, operation, max_retries: int = 3) -> Any:
        """Execute a MongoDB operation with retry logic."""
        if not self._client:
            await self.initialize()
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"MongoDB operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MongoDB operation failed after {max_retries} attempts: {e}")
        
        raise DatabaseConnectionError(f"MongoDB operation failed after {max_retries} attempts: {last_error}")
    
    async def health_check(self) -> bool:
        """Check if the MongoDB connection is healthy."""
        try:
            if not self._client:
                await self.initialize()
            await self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False


class RedisConnection:
    """Redis connection manager with retry logic."""
    
    def __init__(self, connection_url: str, max_connections: int = 20):
        self.connection_url = connection_url
        self.max_connections = max_connections
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the Redis connection pool."""
        if self._client is not None:
            return
            
        async with self._lock:
            if self._client is not None:
                return
                
            try:
                self._pool = redis.ConnectionPool.from_url(
                    self.connection_url,
                    max_connections=self.max_connections,
                    socket_timeout=10,
                    socket_connect_timeout=10,
                    retry_on_timeout=True
                )
                self._client = redis.Redis(connection_pool=self._pool)
                
                # Test the connection
                await self._client.ping()
                logger.info("Redis connection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Redis connection: {e}")
                raise DatabaseConnectionError(f"Redis connection failed: {e}")
    
    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._pool = None
            logger.info("Redis connection closed")
    
    @property
    def client(self):
        """Get the Redis client instance."""
        if not self._client:
            raise DatabaseConnectionError("Redis not initialized")
        return self._client
    
    async def execute_with_retry(self, operation, max_retries: int = 3) -> Any:
        """Execute a Redis operation with retry logic."""
        if not self._client:
            await self.initialize()
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Redis operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Redis operation failed after {max_retries} attempts: {e}")
        
        raise DatabaseConnectionError(f"Redis operation failed after {max_retries} attempts: {last_error}")
    
    async def health_check(self) -> bool:
        """Check if the Redis connection is healthy."""
        try:
            if not self._client:
                await self.initialize()
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


class DatabaseManager:
    """Central database manager for all database connections."""
    
    def __init__(self):
        config = get_memory_config()
        
        self.postgres = PostgreSQLConnection(config.postgres_url)
        
        # Extract database name from MongoDB URL
        mongo_db_name = "memory_db"
        if "/" in config.mongodb_url:
            mongo_db_name = config.mongodb_url.split("/")[-1] or "memory_db"
        
        self.mongodb = MongoDBConnection(config.mongodb_url, mongo_db_name)
        self.redis = RedisConnection(config.redis_url)
        
        self._initialized = False
    
    async def initialize_all(self) -> None:
        """Initialize all database connections."""
        if self._initialized:
            return
            
        try:
            await asyncio.gather(
                self.postgres.initialize(),
                self.mongodb.initialize(),
                self.redis.initialize()
            )
            self._initialized = True
            logger.info("All database connections initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            await self.close_all()
            raise
    
    async def close_all(self) -> None:
        """Close all database connections."""
        await asyncio.gather(
            self.postgres.close(),
            self.mongodb.close(),
            self.redis.close(),
            return_exceptions=True
        )
        self._initialized = False
        logger.info("All database connections closed")
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all database connections."""
        results = await asyncio.gather(
            self.postgres.health_check(),
            self.mongodb.health_check(),
            self.redis.health_check(),
            return_exceptions=True
        )
        
        return {
            "postgres": results[0] if not isinstance(results[0], Exception) else False,
            "mongodb": results[1] if not isinstance(results[1], Exception) else False,
            "redis": results[2] if not isinstance(results[2], Exception) else False
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def initialize_databases() -> None:
    """Initialize all database connections."""
    db_manager = get_database_manager()
    await db_manager.initialize_all()


async def close_databases() -> None:
    """Close all database connections."""
    global _db_manager
    if _db_manager:
        await _db_manager.close_all()
        _db_manager = None