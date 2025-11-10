"""Neo4j database configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jConfig(BaseSettings):
    """
    Configuration for Neo4j database connection.

    Loads configuration from environment variables with sensible defaults.
    Uses Pydantic BaseSettings for automatic validation and type coercion.
    """

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str | None = None  # None = default DB
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0

    def __repr__(self) -> str:
        """Return string representation with password redacted."""
        return (
            f"Neo4jConfig(uri={self.uri!r}, user={self.user!r}, "
            f"database={self.database!r}, max_pool_size={self.max_connection_pool_size})"
        )
