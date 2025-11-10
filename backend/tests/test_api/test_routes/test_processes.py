"""Unit tests for process API routes.

These tests use FastAPI's dependency override system to mock GraphService
interactions and verify that the API routes correctly handle success and error cases.
"""

from datetime import date, datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.routes.processes import get_graph_service_dependency
from src.main import app
from src.schemas.graph import (
    ConfidenceLevel,
    Process,
    ProcessCategory,
    Requirement,
    Step,
)
from src.services.graph_service import ConnectionError, GraphService, GraphServiceError


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock GraphService instance."""
    return MagicMock(spec=GraphService)


@pytest.fixture
def client(mock_service: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client with mocked GraphService dependency."""
    app.dependency_overrides[get_graph_service_dependency] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_process() -> Process:
    """Create a mock Process model."""
    return Process(
        process_id="boston_resident_parking_permit",
        name="Boston Resident Parking Permit",
        description="Process for obtaining a Boston Resident Parking Permit",
        category=ProcessCategory.PERMITS,
        jurisdiction="City of Boston",
        source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
        created_at=datetime(2025, 11, 9, 12, 0, 0),
        updated_at=datetime(2025, 11, 9, 12, 0, 0),
    )


@pytest.fixture
def mock_step() -> Step:
    """Create a mock Step model."""
    return Step(
        step_id="rpp_step_1_check_eligibility",
        process_id="boston_resident_parking_permit",
        name="Check Eligibility",
        description="Verify you meet the basic requirements",
        order=1,
        estimated_time_minutes=10,
        observed_time_minutes=None,
        cost_usd=0.0,
        optional=False,
        source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
        created_at=datetime(2025, 11, 9, 12, 0, 0),
        updated_at=datetime(2025, 11, 9, 12, 0, 0),
    )


@pytest.fixture
def mock_requirement() -> Requirement:
    """Create a mock Requirement model."""
    return Requirement(
        requirement_id="req_residency_proof",
        text="Proof of Boston residency required",
        fact_id="rpp.documents.residency_proof",
        applies_to_process="boston_resident_parking_permit",
        hard_gate=True,
        source_section="Requirements",
        source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
        created_at=datetime(2025, 11, 9, 12, 0, 0),
        updated_at=datetime(2025, 11, 9, 12, 0, 0),
    )


# ==================== GET /api/processes ====================


def test_list_processes_success(
    client: TestClient, mock_service: MagicMock, mock_process: Process
) -> None:
    """Test successful retrieval of all processes."""
    mock_service.get_all_processes = AsyncMock(return_value=[mock_process])

    response = client.get("/api/processes/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["process_id"] == "boston_resident_parking_permit"
    assert data[0]["name"] == "Boston Resident Parking Permit"


def test_list_processes_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test listing processes when database is empty."""
    mock_service.get_all_processes = AsyncMock(return_value=[])

    response = client.get("/api/processes/")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_processes_connection_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of database connection error."""
    mock_service.get_all_processes = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get("/api/processes/")

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


def test_list_processes_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error."""
    mock_service.get_all_processes = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get("/api/processes/")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving processes" in data["detail"]


# ==================== GET /api/processes/{process_id} ====================


def test_get_process_success(
    client: TestClient, mock_service: MagicMock, mock_process: Process
) -> None:
    """Test successful retrieval of a specific process."""
    mock_service.get_process_by_id = AsyncMock(return_value=mock_process)

    response = client.get("/api/processes/boston_resident_parking_permit")

    assert response.status_code == 200
    data = response.json()
    assert data["process_id"] == "boston_resident_parking_permit"
    assert data["name"] == "Boston Resident Parking Permit"
    assert data["category"] == "permits"


def test_get_process_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when process is not found."""
    mock_service.get_process_by_id = AsyncMock(return_value=None)

    response = client.get("/api/processes/nonexistent_process")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_get_process_connection_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of database connection error."""
    mock_service.get_process_by_id = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get("/api/processes/boston_resident_parking_permit")

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


def test_get_process_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error."""
    mock_service.get_process_by_id = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get("/api/processes/boston_resident_parking_permit")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving process" in data["detail"]


# ==================== GET /api/processes/{process_id}/steps ====================


def test_get_process_steps_success(
    client: TestClient, mock_service: MagicMock, mock_step: Step
) -> None:
    """Test successful retrieval of process steps."""
    mock_service.get_process_steps = AsyncMock(return_value=[mock_step])

    response = client.get("/api/processes/boston_resident_parking_permit/steps")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["step_id"] == "rpp_step_1_check_eligibility"
    assert data[0]["name"] == "Check Eligibility"
    assert data[0]["order"] == 1


def test_get_process_steps_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test getting steps for process with no steps."""
    mock_service.get_process_steps = AsyncMock(return_value=[])

    response = client.get("/api/processes/boston_resident_parking_permit/steps")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_process_steps_multiple(
    client: TestClient, mock_service: MagicMock, mock_step: Step
) -> None:
    """Test getting multiple steps ordered correctly."""
    step2 = mock_step.model_copy(
        update={"step_id": "rpp_step_2_gather_docs", "name": "Gather Documents", "order": 2}
    )
    step3 = mock_step.model_copy(
        update={"step_id": "rpp_step_3_submit", "name": "Submit Application", "order": 3}
    )

    mock_service.get_process_steps = AsyncMock(return_value=[mock_step, step2, step3])

    response = client.get("/api/processes/boston_resident_parking_permit/steps")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["order"] == 1
    assert data[1]["order"] == 2
    assert data[2]["order"] == 3


def test_get_process_steps_connection_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of database connection error."""
    mock_service.get_process_steps = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get("/api/processes/boston_resident_parking_permit/steps")

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


# ==================== GET /api/processes/{process_id}/steps/{step_id} ====================


def test_get_step_success(client: TestClient, mock_service: MagicMock, mock_step: Step) -> None:
    """Test successful retrieval of a specific step."""
    mock_service.get_step_by_id = AsyncMock(return_value=mock_step)

    response = client.get(
        "/api/processes/boston_resident_parking_permit/steps/rpp_step_1_check_eligibility"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["step_id"] == "rpp_step_1_check_eligibility"
    assert data["name"] == "Check Eligibility"
    assert data["process_id"] == "boston_resident_parking_permit"


def test_get_step_not_found(client: TestClient, mock_service: MagicMock) -> None:
    """Test 404 response when step is not found."""
    mock_service.get_step_by_id = AsyncMock(return_value=None)

    response = client.get(
        "/api/processes/boston_resident_parking_permit/steps/nonexistent_step"
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_get_step_connection_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of database connection error."""
    mock_service.get_step_by_id = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get(
        "/api/processes/boston_resident_parking_permit/steps/rpp_step_1_check_eligibility"
    )

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


# ==================== GET /api/processes/{process_id}/dag ====================


def test_get_process_dag_success(client: TestClient, mock_service: MagicMock) -> None:
    """Test successful retrieval of process DAG."""
    mock_dag = {
        "nodes": [
            {
                "id": "rpp_step_1_check_eligibility",
                "label": "Check Eligibility",
                "order": 1,
                "data": {"step_id": "rpp_step_1_check_eligibility"},
            },
            {
                "id": "rpp_step_2_gather_docs",
                "label": "Gather Documents",
                "order": 2,
                "data": {"step_id": "rpp_step_2_gather_docs"},
            },
        ],
        "edges": [
            {
                "source": "rpp_step_2_gather_docs",
                "target": "rpp_step_1_check_eligibility",
                "type": "DEPENDS_ON",
            }
        ],
    }

    mock_service.get_process_dag = AsyncMock(return_value=mock_dag)

    response = client.get("/api/processes/boston_resident_parking_permit/dag")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["nodes"][0]["id"] == "rpp_step_1_check_eligibility"


def test_get_process_dag_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test getting DAG for process with no steps."""
    mock_dag = {"nodes": [], "edges": []}

    mock_service.get_process_dag = AsyncMock(return_value=mock_dag)

    response = client.get("/api/processes/boston_resident_parking_permit/dag")

    assert response.status_code == 200
    data = response.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_get_process_dag_connection_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of database connection error."""
    mock_service.get_process_dag = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get("/api/processes/boston_resident_parking_permit/dag")

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


# ==================== GET /api/processes/{process_id}/requirements ====================


def test_get_process_requirements_success(
    client: TestClient, mock_service: MagicMock, mock_requirement: Requirement
) -> None:
    """Test successful retrieval of process requirements."""
    mock_service.get_process_requirements = AsyncMock(return_value=[mock_requirement])

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["requirement_id"] == "req_residency_proof"
    assert data[0]["text"] == "Proof of Boston residency required"
    assert data[0]["hard_gate"] is True


def test_get_process_requirements_empty(client: TestClient, mock_service: MagicMock) -> None:
    """Test getting requirements for process with no requirements."""
    mock_service.get_process_requirements = AsyncMock(return_value=[])

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_process_requirements_multiple(
    client: TestClient, mock_service: MagicMock, mock_requirement: Requirement
) -> None:
    """Test getting multiple requirements."""
    req2 = mock_requirement.model_copy(
        update={
            "requirement_id": "req_ma_registration",
            "text": "MA vehicle registration required",
            "fact_id": "rpp.eligibility.registration_state",
        }
    )

    mock_service.get_process_requirements = AsyncMock(return_value=[mock_requirement, req2])

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["requirement_id"] == "req_residency_proof"
    assert data[1]["requirement_id"] == "req_ma_registration"


def test_get_process_requirements_connection_error(
    client: TestClient, mock_service: MagicMock
) -> None:
    """Test handling of database connection error."""
    mock_service.get_process_requirements = AsyncMock(
        side_effect=ConnectionError("Database connection failed")
    )

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 503
    data = response.json()
    assert "Database connection error" in data["detail"]


def test_get_process_requirements_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error."""
    mock_service.get_process_requirements = AsyncMock(
        side_effect=GraphServiceError("Query failed")
    )

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving requirements" in data["detail"]
