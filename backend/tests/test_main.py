"""Tests for main FastAPI application endpoints."""

from fastapi.testclient import TestClient

from src import __version__


def test_health_check(test_client: TestClient) -> None:
    """Test the health check endpoint returns expected response."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__


def test_root_endpoint(test_client: TestClient) -> None:
    """Test the root endpoint returns API information."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["version"] == __version__
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


def test_docs_available(test_client: TestClient) -> None:
    """Test that API documentation is available."""
    response = test_client.get("/docs")
    assert response.status_code == 200


def test_redoc_available(test_client: TestClient) -> None:
    """Test that ReDoc documentation is available."""
    response = test_client.get("/redoc")
    assert response.status_code == 200
