"""Pytest configuration and shared fixtures."""

from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI application.

    Yields:
        TestClient instance for making synchronous requests.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def async_test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for the FastAPI application.

    Yields:
        AsyncClient instance for making asynchronous requests.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def sample_requirement() -> dict[str, str | int]:
    """
    Sample requirement data for testing.

    Returns:
        Dictionary with sample requirement structure including citations.
    """
    return {
        "requirement": "One proof of residency (<= 30 days)",
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "source_section": "Proof of Boston residency",
        "confidence": "high",
        "last_verified": "2025-11-09",
        "required_count": 1,
        "freshness_days": 30,
    }


@pytest.fixture(scope="function")
def mock_neo4j_session() -> Generator[None, None, None]:
    """
    Mock Neo4j session for testing graph operations.

    TODO: Implement actual mock when Neo4j operations are added.

    Yields:
        Mock session object.
    """
    # Placeholder for future Neo4j mocking
    yield None


@pytest.fixture(scope="function")
def mock_vector_store() -> Generator[None, None, None]:
    """
    Mock vector store for testing RAG operations.

    TODO: Implement actual mock when vector store operations are added.

    Yields:
        Mock vector store object.
    """
    # Placeholder for future vector store mocking
    yield None
