"""Unit tests for facts API routes.

These tests use FastAPI's dependency override system to mock FactsService
interactions and verify that the API routes correctly handle success and error cases.
"""

from collections.abc import Generator
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from src.api.routes.facts import get_facts_service_dependency
from src.main import app
from src.schemas.facts import Fact, FactsRegistry
from src.schemas.graph import ConfidenceLevel
from src.services.facts_service import (
    FactsService,
    FactsServiceError,
    RegistryNotFoundError,
    RegistryParseError,
    RegistryValidationError,
)


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock FactsService instance."""
    return MagicMock(spec=FactsService)


@pytest.fixture
def client(mock_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client with mocked FactsService dependency."""
    app.dependency_overrides[get_facts_service_dependency] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_fact() -> Fact:
    """Create a mock Fact model."""
    return Fact(
        id="rpp.eligibility.vehicle_class",
        text="Vehicle must be a passenger vehicle or motorcycle",
        source_url=HttpUrl(
            "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"
        ),
        source_section="Eligibility Requirements",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def mock_fact_2() -> Fact:
    """Create a second mock Fact model."""
    return Fact(
        id="rpp.eligibility.registration_state",
        text="Vehicle must be registered in Massachusetts",
        source_url=HttpUrl(
            "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"
        ),
        source_section="Eligibility Requirements",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def mock_registry(mock_fact: Fact, mock_fact_2: Fact) -> FactsRegistry:
    """Create a mock FactsRegistry model."""
    return FactsRegistry(
        version="1.0.0",
        last_updated=date(2025, 11, 9),
        scope="boston_resident_parking_permit",
        facts=[mock_fact, mock_fact_2],
    )


# ==================== GET /api/facts ====================


def test_list_facts_all_success(
    client: TestClient, mock_service: MagicMock, mock_fact: Fact
) -> None:
    """Test successful retrieval of all facts from all loaded registries."""
    mock_service.get_all_facts.return_value = [mock_fact]

    response = client.get("/api/facts/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "rpp.eligibility.vehicle_class"
    assert data[0]["text"] == "Vehicle must be a passenger vehicle or motorcycle"
    assert data[0]["confidence"] == "high"


def test_list_facts_by_registry_success(
    client: TestClient, mock_service: MagicMock, mock_registry: FactsRegistry
) -> None:
    """Test successful retrieval of facts filtered by registry name."""
    mock_service.load_registry.return_value = mock_registry

    response = client.get("/api/facts/?registry_name=boston_rpp")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == "rpp.eligibility.vehicle_class"
    assert data[1]["id"] == "rpp.eligibility.registration_state"
    mock_service.load_registry.assert_called_once_with("boston_rpp")


def test_list_facts_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test listing facts when no registries are loaded."""
    mock_service.get_all_facts.return_value = []

    response = client.get("/api/facts/")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_facts_registry_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when specified registry is not found."""
    mock_service.load_registry.side_effect = RegistryNotFoundError(
        "Registry 'nonexistent' not found"
    )

    response = client.get("/api/facts/?registry_name=nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_list_facts_registry_parse_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test 500 response when registry YAML cannot be parsed."""
    mock_service.load_registry.side_effect = RegistryParseError("Failed to parse YAML")

    response = client.get("/api/facts/?registry_name=boston_rpp")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_list_facts_registry_validation_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test 500 response when registry fails Pydantic validation."""
    mock_service.load_registry.side_effect = RegistryValidationError("Registry validation failed")

    response = client.get("/api/facts/?registry_name=boston_rpp")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_list_facts_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error."""
    mock_service.get_all_facts.side_effect = FactsServiceError("Service error")

    response = client.get("/api/facts/")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving facts" in data["detail"]


# ==================== GET /api/facts/search ====================


def test_search_facts_success(
    client: TestClient, mock_service: MagicMock, mock_fact: Fact, mock_fact_2: Fact
) -> None:
    """Test successful search for facts by prefix."""
    mock_service.get_facts_by_prefix.return_value = [mock_fact, mock_fact_2]

    response = client.get("/api/facts/search?prefix=rpp.eligibility")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == "rpp.eligibility.vehicle_class"
    assert data[1]["id"] == "rpp.eligibility.registration_state"
    mock_service.get_facts_by_prefix.assert_called_once_with("rpp.eligibility")


def test_search_facts_no_matches(client: TestClient, mock_service: MagicMock) -> None:
    """Test search that returns no results."""
    mock_service.get_facts_by_prefix.return_value = []

    response = client.get("/api/facts/search?prefix=nonexistent.prefix")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_search_facts_missing_prefix(client: TestClient, mock_service: MagicMock) -> None:
    """Test that prefix parameter is required."""
    response = client.get("/api/facts/search")

    assert response.status_code == 422  # Validation error


def test_search_facts_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of service error during search."""
    mock_service.get_facts_by_prefix.side_effect = FactsServiceError("Search failed")

    response = client.get("/api/facts/search?prefix=rpp.")

    assert response.status_code == 500
    data = response.json()
    assert "Error searching facts" in data["detail"]


# ==================== GET /api/facts/{fact_id} ====================


def test_get_fact_success(client: TestClient, mock_service: MagicMock, mock_fact: Fact) -> None:
    """Test successful retrieval of a specific fact by ID."""
    mock_service.get_fact_by_id.return_value = mock_fact

    response = client.get("/api/facts/rpp.eligibility.vehicle_class")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "rpp.eligibility.vehicle_class"
    assert data["text"] == "Vehicle must be a passenger vehicle or motorcycle"
    assert data["confidence"] == "high"
    assert data["source_url"] is not None
    mock_service.get_fact_by_id.assert_called_once_with("rpp.eligibility.vehicle_class")


def test_get_fact_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when fact is not found."""
    mock_service.get_fact_by_id.return_value = None

    response = client.get("/api/facts/nonexistent.fact.id")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_get_fact_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error."""
    mock_service.get_fact_by_id.side_effect = FactsServiceError("Service error")

    response = client.get("/api/facts/rpp.eligibility.vehicle_class")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving fact" in data["detail"]


# ==================== GET /api/registries ====================


def test_list_registries_success(client: TestClient, mock_service: MagicMock) -> None:
    """Test successful retrieval of loaded registries."""
    mock_service.get_loaded_registries.return_value = ["boston_rpp", "cambridge_parking"]

    response = client.get("/api/registries/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert "boston_rpp" in data
    assert "cambridge_parking" in data


def test_list_registries_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test listing registries when none are loaded."""
    mock_service.get_loaded_registries.return_value = []

    response = client.get("/api/registries/")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_registries_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of service error when listing registries."""
    mock_service.get_loaded_registries.side_effect = FactsServiceError("Service error")

    response = client.get("/api/registries/")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving registries" in data["detail"]


# ==================== GET /api/registries/{registry_name} ====================


def test_get_registry_metadata_success(
    client: TestClient, mock_service: MagicMock, mock_registry: FactsRegistry
) -> None:
    """Test successful retrieval of registry metadata."""
    mock_service.load_registry.return_value = mock_registry
    mock_service.get_registry_info.return_value = {
        "registry_name": "boston_rpp",
        "version": "1.0.0",
        "scope": "boston_resident_parking_permit",
        "last_updated": "2025-11-09",
        "fact_count": 2,
    }

    response = client.get("/api/registries/boston_rpp")

    assert response.status_code == 200
    data = response.json()
    assert data["registry_name"] == "boston_rpp"
    assert data["version"] == "1.0.0"
    assert data["scope"] == "boston_resident_parking_permit"
    assert data["fact_count"] == 2
    mock_service.load_registry.assert_called_once_with("boston_rpp")
    mock_service.get_registry_info.assert_called_once_with("boston_rpp")


def test_get_registry_metadata_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when registry is not found."""
    mock_service.load_registry.side_effect = RegistryNotFoundError(
        "Registry 'nonexistent' not found"
    )

    response = client.get("/api/registries/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_get_registry_metadata_parse_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test 500 response when registry cannot be parsed."""
    mock_service.load_registry.side_effect = RegistryParseError("Failed to parse YAML")

    response = client.get("/api/registries/boston_rpp")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_get_registry_metadata_validation_error(
    client: TestClient, mock_service: MagicMock
) -> None:
    """Test 500 response when registry fails validation."""
    mock_service.load_registry.side_effect = RegistryValidationError("Registry validation failed")

    response = client.get("/api/registries/boston_rpp")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_get_registry_metadata_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of service error when getting metadata."""
    mock_service.load_registry.return_value = MagicMock()
    mock_service.get_registry_info.side_effect = FactsServiceError("Service error")

    response = client.get("/api/registries/boston_rpp")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving registry metadata" in data["detail"]


# ==================== POST /api/registries/{registry_name}/load ====================


def test_load_registry_success(
    client: TestClient, mock_service: MagicMock, mock_registry: FactsRegistry
) -> None:
    """Test successful loading of a registry."""
    mock_service.load_registry.return_value = mock_registry

    response = client.post("/api/registries/boston_rpp/load")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "loaded"
    assert data["registry_name"] == "boston_rpp"
    assert data["version"] == "1.0.0"
    assert data["scope"] == "boston_resident_parking_permit"
    assert data["fact_count"] == 2
    mock_service.load_registry.assert_called_once_with("boston_rpp")


def test_load_registry_reload_success(
    client: TestClient, mock_service: MagicMock, mock_registry: FactsRegistry
) -> None:
    """Test successful reload of a registry from disk."""
    mock_service.reload_registry.return_value = mock_registry

    response = client.post("/api/registries/boston_rpp/load?reload=true")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reloaded"
    assert data["registry_name"] == "boston_rpp"
    assert data["version"] == "1.0.0"
    mock_service.reload_registry.assert_called_once_with("boston_rpp")


def test_load_registry_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when registry file is not found."""
    mock_service.load_registry.side_effect = RegistryNotFoundError(
        "Registry 'nonexistent' not found"
    )

    response = client.post("/api/registries/nonexistent/load")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_load_registry_parse_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test 500 response when registry cannot be parsed."""
    mock_service.load_registry.side_effect = RegistryParseError("Failed to parse YAML")

    response = client.post("/api/registries/boston_rpp/load")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_load_registry_validation_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test 500 response when registry fails validation."""
    mock_service.load_registry.side_effect = RegistryValidationError("Registry validation failed")

    response = client.post("/api/registries/boston_rpp/load")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]


def test_load_registry_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error during load."""
    mock_service.load_registry.side_effect = FactsServiceError("Service error")

    response = client.post("/api/registries/boston_rpp/load")

    assert response.status_code == 500
    data = response.json()
    assert "Error loading registry" in data["detail"]
