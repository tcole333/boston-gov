"""Neo4j database client with connection pooling and health checks."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j database client with connection pooling and lifecycle management.

    This class implements a singleton pattern and provides:
    - Connection pooling via Neo4j driver
    - Health check capabilities
    - Proper cleanup of resources
    - FastAPI dependency injection compatibility

    Example:
        ```python
        client = Neo4jClient()
        await client.connect()

        # Check health
        is_healthy = await client.health_check()

        # Get session
        async with client.get_session() as session:
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            print(record["count"])

        # Cleanup
        await client.close()
        ```
    """

    _instance: Optional["Neo4jClient"] = None
    _driver: AsyncDriver | None = None
    _config: Neo4jConfig | None = None

    def __new__(cls) -> "Neo4jClient":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize client (config loaded on connect())."""
        pass

    async def connect(self, config: Neo4jConfig | None = None) -> None:
        """
        Initialize Neo4j driver with connection pooling.

        Args:
            config: Optional Neo4jConfig instance. If None, loads from environment.

        Raises:
            ServiceUnavailable: If cannot connect to Neo4j
            Neo4jError: For other Neo4j-related errors
        """
        if self._driver is not None:
            logger.warning("Neo4j driver already connected")
            return

        self._config = config or Neo4jConfig()

        try:
            logger.info(f"Connecting to Neo4j at {self._config.uri}")
            self._driver = AsyncGraphDatabase.driver(
                self._config.uri,
                auth=(self._config.user, self._config.password),
                max_connection_lifetime=self._config.max_connection_lifetime,
                max_connection_pool_size=self._config.max_connection_pool_size,
                connection_timeout=self._config.connection_timeout,
            )

            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")

        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
        except Neo4jError as e:
            logger.error(f"Neo4j error during connection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close Neo4j driver and cleanup resources."""
        if self._driver is not None:
            logger.info("Closing Neo4j driver")
            await self._driver.close()
            self._driver = None
            self._config = None
            logger.info("Neo4j driver closed")

    @asynccontextmanager
    async def get_session(self, database: str | None = None) -> AsyncIterator[AsyncSession]:
        """
        Get a Neo4j session as an async context manager.

        Args:
            database: Optional database name. If None, uses default from config.

        Yields:
            AsyncSession: Active Neo4j session

        Raises:
            RuntimeError: If driver not connected
            Neo4jError: For Neo4j-related errors

        Example:
            ```python
            async with client.get_session() as session:
                result = await session.run("MATCH (n:Process) RETURN n")
                async for record in result:
                    print(record["n"])
            ```
        """
        if self._driver is None:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        db = database or (self._config.database if self._config else None)

        async with self._driver.session(database=db) as session:
            try:
                yield session
            except Neo4jError as e:
                logger.error(f"Neo4j error during session: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during session: {e}")
                raise

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on Neo4j connection.

        Returns:
            Dict with health status:
            - status: "healthy" or "unhealthy"
            - details: Additional information
            - error: Error message if unhealthy

        Example:
            ```python
            health = await client.health_check()
            if health["status"] == "healthy":
                print("Neo4j is accessible")
            ```
        """
        if self._driver is None:
            return {
                "status": "unhealthy",
                "details": "Driver not connected",
                "error": "Neo4j driver has not been initialized",
            }

        try:
            # Try to verify connectivity
            await self._driver.verify_connectivity()

            # Run a simple query to verify database is accessible
            async with self.get_session() as session:
                result = await session.run("RETURN 1 as health_check")
                record = await result.single()
                if record and record["health_check"] == 1:
                    return {
                        "status": "healthy",
                        "details": {
                            "uri": self._config.uri if self._config else "unknown",
                            "database": self._config.database if self._config else "default",
                        },
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "details": "Query returned unexpected result",
                        "error": "Health check query failed",
                    }

        except ServiceUnavailable as e:
            logger.error(f"Neo4j health check failed - service unavailable: {e}")
            return {
                "status": "unhealthy",
                "details": "Service unavailable",
                "error": str(e),
            }
        except Neo4jError as e:
            logger.error(f"Neo4j health check failed - Neo4j error: {e}")
            return {
                "status": "unhealthy",
                "details": "Neo4j error",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Neo4j health check failed - unexpected error: {e}")
            return {
                "status": "unhealthy",
                "details": "Unexpected error",
                "error": str(e),
            }


# Singleton instance for FastAPI dependency injection
_neo4j_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get or create the singleton Neo4j client instance.

    This function is designed for use with FastAPI dependency injection.

    Returns:
        Neo4jClient: The singleton client instance

    Example:
        ```python
        from fastapi import Depends
        from src.db.graph.client import get_neo4j_client, Neo4jClient

        @app.get("/processes/{process_id}")
        async def get_process(
            process_id: str,
            neo4j: Neo4jClient = Depends(get_neo4j_client)
        ):
            async with neo4j.get_session() as session:
                result = await session.run(
                    "MATCH (p:Process {id: $id}) RETURN p",
                    id=process_id
                )
                record = await result.single()
                return record["p"]
        ```
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
