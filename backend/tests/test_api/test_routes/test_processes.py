"""Unit tests for process API routes.

These tests use FastAPI's dependency override system to mock GraphService
interactions and verify that the API routes correctly handle success and error cases.
"""

from collections.abc import Generator
from datetime import date, datetime
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


def test_get_process_steps_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error when getting steps."""
    mock_service.get_process_steps = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get("/api/processes/boston_resident_parking_permit/steps")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving steps" in data["detail"]


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

    response = client.get("/api/processes/boston_resident_parking_permit/steps/nonexistent_step")

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


def test_get_step_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error when getting a step."""
    mock_service.get_step_by_id = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get(
        "/api/processes/boston_resident_parking_permit/steps/rpp_step_1_check_eligibility"
    )

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving step" in data["detail"]


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


def test_get_process_dag_service_error(client: TestClient, mock_service: MagicMock) -> None:
    """Test handling of general service error when getting DAG."""
    mock_service.get_process_dag = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get("/api/processes/boston_resident_parking_permit/dag")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving DAG" in data["detail"]


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


def test_get_process_requirements_service_error(
    client: TestClient, mock_service: MagicMock
) -> None:
    """Test handling of general service error."""
    mock_service.get_process_requirements = AsyncMock(side_effect=GraphServiceError("Query failed"))

    response = client.get("/api/processes/boston_resident_parking_permit/requirements")

    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving requirements" in data["detail"]


# ==================== GET /api/processes/{process_id}/document-types ====================


def test_get_document_types_boston_rpp(client: TestClient) -> None:
    """Test document types endpoint for Boston RPP process."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    # Should return 3 document types
    assert len(data) == 3

    # Verify structure of first document type
    doc = data[0]
    assert "id" in doc
    assert "label" in doc
    assert "description" in doc
    assert "accepted_formats" in doc
    assert "max_size_mb" in doc
    assert "required" in doc

    # Verify citations present
    assert "source_url" in doc
    assert "source_section" in doc
    assert "last_verified" in doc
    assert "confidence" in doc

    # Verify specific document types
    doc_ids = {d["id"] for d in data}
    assert "proof_of_residency" in doc_ids
    assert "vehicle_registration" in doc_ids
    assert "drivers_license" in doc_ids


def test_get_document_types_boston_rpp_details(client: TestClient) -> None:
    """Test detailed fields of Boston RPP document types."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    # Verify proof_of_residency details
    proof_of_residency = next(d for d in data if d["id"] == "proof_of_residency")
    assert proof_of_residency["label"] == "Proof of Boston Residency"
    assert "utility bill" in proof_of_residency["description"].lower()
    assert "pdf" in proof_of_residency["accepted_formats"]
    assert "jpg" in proof_of_residency["accepted_formats"]
    assert "png" in proof_of_residency["accepted_formats"]
    assert proof_of_residency["max_size_mb"] == 10
    assert proof_of_residency["required"] is True

    # Verify vehicle_registration details
    vehicle_reg = next(d for d in data if d["id"] == "vehicle_registration")
    assert vehicle_reg["label"] == "Vehicle Registration"
    assert "massachusetts" in vehicle_reg["description"].lower()
    assert vehicle_reg["required"] is True

    # Verify drivers_license details
    drivers_license = next(d for d in data if d["id"] == "drivers_license")
    assert drivers_license["label"] == "Driver's License"
    assert "massachusetts" in drivers_license["description"].lower()
    assert drivers_license["required"] is True


def test_get_document_types_citations_valid(client: TestClient) -> None:
    """Test that all document types have valid citations."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    for doc in data:
        # Verify citations
        assert doc["source_url"].startswith("https://")
        assert "boston.gov" in doc["source_url"]
        assert len(doc["source_section"]) > 0
        # Verify YYYY-MM-DD format
        assert len(doc["last_verified"]) == 10
        assert doc["last_verified"].count("-") == 2
        # Verify confidence level
        assert doc["confidence"] in ["high", "medium", "low"]


def test_get_document_types_unknown_process(client: TestClient) -> None:
    """Test document types for unknown process returns empty list."""
    response = client.get("/api/processes/unknown_process/document-types")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_document_types_accepted_formats(client: TestClient) -> None:
    """Test that all document types accept common file formats."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    for doc in data:
        # All documents should accept at least pdf, jpg, png
        formats = doc["accepted_formats"]
        assert "pdf" in formats
        assert "jpg" in formats or "jpeg" in formats
        assert "png" in formats
        # Max size should be reasonable
        assert 1 <= doc["max_size_mb"] <= 100


def test_get_document_types_all_required(client: TestClient) -> None:
    """Test that all Boston RPP document types are marked as required."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    for doc in data:
        assert doc["required"] is True, f"Document {doc['id']} should be required"


def test_get_document_types_source_consistency(client: TestClient) -> None:
    """Test that all document types cite the same verified date."""
    response = client.get("/api/processes/boston_resident_parking_permit/document-types")

    assert response.status_code == 200
    data = response.json()

    # All should have the same last_verified date (from same source)
    verified_dates = {d["last_verified"] for d in data}
    assert len(verified_dates) == 1, "All documents should have same verification date"

    # All should have high confidence (official source)
    confidences = {d["confidence"] for d in data}
    assert confidences == {"high"}, "All documents should have high confidence"
