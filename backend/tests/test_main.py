"""Tests for main FastAPI application endpoints."""

import os
from unittest.mock import patch

import pytest
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


class TestCORSConfiguration:
    """Tests for CORS middleware configuration in different environments."""

    def test_development_cors_allows_any_localhost_port(self, test_client: TestClient) -> None:
        """Test that development mode allows requests from any localhost port."""
        # Test various localhost ports
        test_origins = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:9999",
        ]

        for origin in test_origins:
            response = test_client.options(
                "/health",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            # CORS preflight should succeed for all localhost ports
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

    def test_development_cors_rejects_non_localhost(self, test_client: TestClient) -> None:
        """Test that development mode rejects non-localhost origins."""
        non_localhost_origins = [
            "http://example.com",
            "https://malicious.com",
            "http://192.168.1.1:5173",
        ]

        for origin in non_localhost_origins:
            response = test_client.options(
                "/health",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Should not have CORS headers for non-localhost
            assert "access-control-allow-origin" not in response.headers or (
                origin not in response.headers.get("access-control-allow-origin", "")
            )

    @patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": "https://example.com,https://app.example.com"})
    def test_production_cors_requires_explicit_origins(self) -> None:
        """Test that production mode enforces strict origin list."""
        # Need to reimport to pick up new environment
        import importlib

        import src.main

        importlib.reload(src.main)

        with TestClient(src.main.app) as client:
            # Allowed origin should work
            response = client.options(
                "/health",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

            # Disallowed origin should not have CORS headers
            response = client.options(
                "/health",
                headers={
                    "Origin": "https://malicious.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # FastAPI returns 400 for disallowed origins in CORS preflight
            assert response.status_code == 400

    @patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": ""})
    def test_production_without_cors_origins_raises_error(self) -> None:
        """Test that production mode raises error if CORS_ORIGINS not set."""
        import importlib

        import src.main

        # Reloading should raise ValueError during app initialization
        with pytest.raises(ValueError, match="CORS_ORIGINS environment variable must be set in production"):
            importlib.reload(src.main)

    @patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": "https://example.com"})
    def test_production_cors_blocks_localhost(self) -> None:
        """Test that production mode blocks localhost origins."""
        import importlib

        import src.main

        importlib.reload(src.main)

        with TestClient(src.main.app) as client:
            # Localhost should be blocked in production
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Should return 400 for disallowed origin
            assert response.status_code == 400
