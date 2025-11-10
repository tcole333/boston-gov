"""Tests for Neo4j client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from neo4j.exceptions import ServiceUnavailable, Neo4jError

from src.db.graph.client import Neo4jClient, get_neo4j_client
from src.db.graph.config import Neo4jConfig


class TestNeo4jConfig:
    """Test Neo4j configuration."""

    def test_config_defaults(self) -> None:
        """Test configuration loads with default values."""
        config = Neo4jConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == "password"
        assert config.database is None
        assert config.max_connection_lifetime == 3600
        assert config.max_connection_pool_size == 50
        assert config.connection_timeout == 30.0

    def test_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test configuration loads from environment variables."""
        monkeypatch.setenv("NEO4J_URI", "bolt://test:7687")
        monkeypatch.setenv("NEO4J_USER", "testuser")
        monkeypatch.setenv("NEO4J_PASSWORD", "testpass")
        monkeypatch.setenv("NEO4J_DATABASE", "testdb")
        monkeypatch.setenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "100")

        config = Neo4jConfig()
        assert config.uri == "bolt://test:7687"
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.database == "testdb"
        assert config.max_connection_pool_size == 100

    def test_config_repr_masks_password(self) -> None:
        """Test that repr doesn't expose password."""
        config = Neo4jConfig()
        repr_str = repr(config)
        assert "password" not in repr_str
        assert "neo4j" in repr_str
        assert "bolt://localhost:7687" in repr_str


class TestNeo4jClient:
    """Test Neo4j client."""

    @pytest.fixture
    def mock_driver(self) -> AsyncMock:
        """Create a mock Neo4j driver."""
        driver = AsyncMock()
        driver.verify_connectivity = AsyncMock()
        driver.close = AsyncMock()
        return driver

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock Neo4j session."""
        session = AsyncMock()
        result = AsyncMock()
        record = MagicMock()
        record.__getitem__ = lambda self, key: 1 if key == "health_check" else None
        result.single = AsyncMock(return_value=record)
        session.run = AsyncMock(return_value=result)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton state before each test."""
        Neo4jClient._instance = None
        Neo4jClient._driver = None
        Neo4jClient._config = None

    def test_singleton_pattern(self) -> None:
        """Test that Neo4jClient follows singleton pattern."""
        client1 = Neo4jClient()
        client2 = Neo4jClient()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_driver: AsyncMock) -> None:
        """Test successful connection to Neo4j."""
        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            config = Neo4jConfig(uri="bolt://test:7687", user="test", password="test")

            await client.connect(config)

            mock_driver.verify_connectivity.assert_awaited_once()
            assert client._driver is not None
            assert client._config is not None

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, mock_driver: AsyncMock) -> None:
        """Test connecting when already connected logs warning."""
        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            # Connect again
            with patch("src.db.graph.client.logger") as mock_logger:
                await client.connect()
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_service_unavailable(self) -> None:
        """Test connection failure when service unavailable."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock(
            side_effect=ServiceUnavailable("Cannot connect")
        )

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()

            with pytest.raises(ServiceUnavailable):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_neo4j_error(self) -> None:
        """Test connection failure with Neo4j error."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock(
            side_effect=Neo4jError("Auth failed")
        )

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()

            with pytest.raises(Neo4jError):
                await client.connect()

    @pytest.mark.asyncio
    async def test_close(self, mock_driver: AsyncMock) -> None:
        """Test closing the driver."""
        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            await client.close()

            mock_driver.close.assert_awaited_once()
            assert client._driver is None
            assert client._config is None

    @pytest.mark.asyncio
    async def test_get_session_not_connected(self) -> None:
        """Test get_session raises error when not connected."""
        client = Neo4jClient()

        with pytest.raises(RuntimeError, match="not connected"):
            async with client.get_session():
                pass

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, mock_driver: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test getting a session successfully."""
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            async with client.get_session() as session:
                assert session is not None
                # Verify we can run queries
                result = await session.run("RETURN 1")
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_session_with_database(
        self, mock_driver: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test getting a session with specific database."""
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            async with client.get_session(database="testdb") as session:
                assert session is not None

            mock_driver.session.assert_called_with(database="testdb")

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self) -> None:
        """Test health check when driver not connected."""
        client = Neo4jClient()

        health = await client.health_check()

        assert health["status"] == "unhealthy"
        assert "not connected" in health["details"].lower()
        assert "error" in health

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, mock_driver: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test successful health check."""
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            config = Neo4jConfig(uri="bolt://test:7687")
            await client.connect(config)

            health = await client.health_check()

            assert health["status"] == "healthy"
            assert "bolt://test:7687" in health["details"]["uri"]
            mock_driver.verify_connectivity.assert_awaited()

    @pytest.mark.asyncio
    async def test_health_check_service_unavailable(self, mock_driver: AsyncMock) -> None:
        """Test health check when service unavailable."""
        # First allow connection to succeed
        mock_driver.verify_connectivity = AsyncMock()

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            # Now make verify_connectivity fail on health check
            mock_driver.verify_connectivity = AsyncMock(
                side_effect=ServiceUnavailable("Service down")
            )

            health = await client.health_check()

            assert health["status"] == "unhealthy"
            assert "unavailable" in health["details"].lower()
            assert "Service down" in health["error"]

    @pytest.mark.asyncio
    async def test_health_check_neo4j_error(
        self, mock_driver: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Test health check with Neo4j error."""
        # Make verify_connectivity succeed but session.run fail
        mock_session.run = AsyncMock(side_effect=Neo4jError("Query failed"))
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch("src.db.graph.client.AsyncGraphDatabase.driver", return_value=mock_driver):
            client = Neo4jClient()
            await client.connect()

            health = await client.health_check()

            assert health["status"] == "unhealthy"
            assert "Query failed" in health["error"]

    def test_get_neo4j_client_returns_singleton(self) -> None:
        """Test get_neo4j_client returns singleton instance."""
        client1 = get_neo4j_client()
        client2 = get_neo4j_client()
        assert client1 is client2
        assert isinstance(client1, Neo4jClient)


@pytest.mark.integration
class TestNeo4jClientIntegration:
    """Integration tests with real Neo4j instance."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton state before each test."""
        Neo4jClient._instance = None
        Neo4jClient._driver = None
        Neo4jClient._config = None

    @pytest.mark.asyncio
    async def test_real_connection(self) -> None:
        """
        Test actual connection to Neo4j.

        Requires Neo4j running on bolt://localhost:7687.
        Run with: pytest -v -m integration
        """
        client = Neo4jClient()

        try:
            await client.connect()

            # Test health check
            health = await client.health_check()
            assert health["status"] == "healthy"

            # Test session
            async with client.get_session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                assert record["test"] == 1

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_real_connection_invalid_credentials(self) -> None:
        """Test connection with invalid credentials."""
        client = Neo4jClient()
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="invalid",
            password="invalid"
        )

        with pytest.raises((ServiceUnavailable, Neo4jError)):
            await client.connect(config)

        await client.close()
