"""Unit tests for GraphService with mocked Neo4j driver.

These tests use pytest-mock to mock Neo4j interactions and verify
that the GraphService correctly transforms Neo4j data into Pydantic models.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.graph.client import Neo4jClient
from src.schemas.graph import (
    ConfidenceLevel,
    DocumentType,
    Office,
    Process,
    ProcessCategory,
    Requirement,
    RPPNeighborhood,
    Rule,
    Step,
)
from src.services.graph_service import (
    ConnectionError,
    GraphService,
    GraphServiceError,
    get_graph_service,
)


@pytest.fixture
def mock_neo4j_client():
    """Create a mocked Neo4jClient."""
    client = MagicMock(spec=Neo4jClient)
    return client


@pytest.fixture
def graph_service(mock_neo4j_client):
    """Create a GraphService with mocked client."""
    return GraphService(mock_neo4j_client)


@pytest.fixture
def sample_process_data():
    """Sample process node data from Neo4j."""
    return {
        "process_id": "boston_resident_parking_permit",
        "name": "Boston Resident Parking Permit",
        "description": "Process for obtaining a Boston Resident Parking Permit",
        "category": "permits",
        "jurisdiction": "City of Boston",
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }


@pytest.fixture
def sample_step_data():
    """Sample step node data from Neo4j."""
    return {
        "step_id": "rpp_step_1_check_eligibility",
        "process_id": "boston_resident_parking_permit",
        "name": "Check Eligibility",
        "description": "Verify you meet the basic requirements",
        "order": 1,
        "estimated_time_minutes": 10,
        "observed_time_minutes": None,
        "cost_usd": 0.0,
        "optional": False,
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }


@pytest.fixture
def sample_requirement_data():
    """Sample requirement node data from Neo4j."""
    return {
        "requirement_id": "req_residency_proof",
        "text": "Proof of Boston residency required",
        "fact_id": "rpp.documents.residency_proof",
        "applies_to_process": "boston_resident_parking_permit",
        "hard_gate": True,
        "source_section": "Requirements",
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }


# ==================== Process Query Tests ====================


@pytest.mark.asyncio
async def test_get_process_by_id_success(graph_service, mock_neo4j_client, sample_process_data):
    """Test successful retrieval of a process by ID."""
    # Mock the session context manager
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"p": sample_process_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    process = await graph_service.get_process_by_id("boston_resident_parking_permit")

    # Assert
    assert process is not None
    assert isinstance(process, Process)
    assert process.process_id == "boston_resident_parking_permit"
    assert process.name == "Boston Resident Parking Permit"
    assert process.category == ProcessCategory.PERMITS
    assert process.confidence == ConfidenceLevel.HIGH


@pytest.mark.asyncio
async def test_get_process_by_id_not_found(graph_service, mock_neo4j_client):
    """Test retrieval of a non-existent process."""
    # Mock empty result
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    process = await graph_service.get_process_by_id("nonexistent_process")

    # Assert
    assert process is None


@pytest.mark.asyncio
async def test_get_all_processes(graph_service, mock_neo4j_client, sample_process_data):
    """Test retrieval of all processes."""
    # Mock result with multiple processes
    process_2 = sample_process_data.copy()
    process_2["process_id"] = "another_process"
    process_2["name"] = "Another Process"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"p": sample_process_data}, {"p": process_2}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    processes = await graph_service.get_all_processes()

    # Assert
    assert len(processes) == 2
    assert all(isinstance(p, Process) for p in processes)
    assert processes[0].process_id == "boston_resident_parking_permit"
    assert processes[1].process_id == "another_process"


@pytest.mark.asyncio
async def test_get_processes_by_category(graph_service, mock_neo4j_client, sample_process_data):
    """Test retrieval of processes by category."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"p": sample_process_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    processes = await graph_service.get_processes_by_category("permits")

    # Assert
    assert len(processes) == 1
    assert processes[0].category == ProcessCategory.PERMITS


# ==================== Step Query Tests ====================


@pytest.mark.asyncio
async def test_get_step_by_id_success(graph_service, mock_neo4j_client, sample_step_data):
    """Test successful retrieval of a step by ID."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"s": sample_step_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    step = await graph_service.get_step_by_id("rpp_step_1_check_eligibility")

    # Assert
    assert step is not None
    assert isinstance(step, Step)
    assert step.step_id == "rpp_step_1_check_eligibility"
    assert step.name == "Check Eligibility"
    assert step.order == 1


@pytest.mark.asyncio
async def test_get_process_steps(graph_service, mock_neo4j_client, sample_step_data):
    """Test retrieval of all steps for a process."""
    # Create multiple steps
    step_2 = sample_step_data.copy()
    step_2["step_id"] = "rpp_step_2_gather_documents"
    step_2["name"] = "Gather Documents"
    step_2["order"] = 2

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"s": sample_step_data}, {"s": step_2}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    steps = await graph_service.get_process_steps("boston_resident_parking_permit")

    # Assert
    assert len(steps) == 2
    assert all(isinstance(s, Step) for s in steps)
    assert steps[0].order == 1
    assert steps[1].order == 2


@pytest.mark.asyncio
async def test_get_step_dependencies(graph_service, mock_neo4j_client, sample_step_data):
    """Test retrieval of step dependencies."""
    # Create a dependency step
    dep_step = sample_step_data.copy()
    dep_step["step_id"] = "rpp_step_1_check_eligibility"
    dep_step["order"] = 1

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"dep": dep_step}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    dependencies = await graph_service.get_step_dependencies("rpp_step_2_gather_documents")

    # Assert
    assert len(dependencies) == 1
    assert dependencies[0].step_id == "rpp_step_1_check_eligibility"


# ==================== Requirement Query Tests ====================


@pytest.mark.asyncio
async def test_get_requirement_by_id(graph_service, mock_neo4j_client, sample_requirement_data):
    """Test retrieval of a requirement by ID."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"r": sample_requirement_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    requirement = await graph_service.get_requirement_by_id("req_residency_proof")

    # Assert
    assert requirement is not None
    assert isinstance(requirement, Requirement)
    assert requirement.requirement_id == "req_residency_proof"
    assert requirement.hard_gate is True


@pytest.mark.asyncio
async def test_get_process_requirements(graph_service, mock_neo4j_client, sample_requirement_data):
    """Test retrieval of all requirements for a process."""
    req_2 = sample_requirement_data.copy()
    req_2["requirement_id"] = "req_vehicle_registration"
    req_2["text"] = "Valid vehicle registration required"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"r": sample_requirement_data}, {"r": req_2}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    requirements = await graph_service.get_process_requirements("boston_resident_parking_permit")

    # Assert
    assert len(requirements) == 2
    assert all(isinstance(r, Requirement) for r in requirements)


@pytest.mark.asyncio
async def test_get_hard_gate_requirements(
    graph_service, mock_neo4j_client, sample_requirement_data
):
    """Test retrieval of hard-gate requirements only."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"r": sample_requirement_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    requirements = await graph_service.get_hard_gate_requirements("boston_resident_parking_permit")

    # Assert
    assert len(requirements) == 1
    assert requirements[0].hard_gate is True


# ==================== Document Type Query Tests ====================


@pytest.mark.asyncio
async def test_get_document_type_by_id(graph_service, mock_neo4j_client):
    """Test retrieval of a document type by ID."""
    doc_type_data = {
        "doc_type_id": "proof.utility_bill",
        "name": "Utility Bill",
        "freshness_days": 30,
        "name_match_required": True,
        "address_match_required": True,
        "examples": ["National Grid", "Eversource"],
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"dt": doc_type_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    doc_type = await graph_service.get_document_type_by_id("proof.utility_bill")

    # Assert
    assert doc_type is not None
    assert isinstance(doc_type, DocumentType)
    assert doc_type.doc_type_id == "proof.utility_bill"
    assert doc_type.freshness_days == 30


@pytest.mark.asyncio
async def test_get_step_document_types(graph_service, mock_neo4j_client):
    """Test retrieval of document types needed for a step."""
    doc_type_data = {
        "doc_type_id": "proof.utility_bill",
        "name": "Utility Bill",
        "freshness_days": 30,
        "name_match_required": True,
        "address_match_required": True,
        "examples": ["National Grid"],
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"dt": doc_type_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    doc_types = await graph_service.get_step_document_types("rpp_step_2_gather_documents")

    # Assert
    assert len(doc_types) == 1
    assert doc_types[0].doc_type_id == "proof.utility_bill"


# ==================== Office Query Tests ====================


@pytest.mark.asyncio
async def test_get_office_by_id(graph_service, mock_neo4j_client):
    """Test retrieval of an office by ID."""
    office_data = {
        "office_id": "boston_parking_clerk",
        "name": "Boston Parking Clerk",
        "address": "1 City Hall Square, Room 224, Boston, MA 02201",
        "room": "224",
        "hours": "Mon-Fri, 9:00-4:30",
        "phone": "617-635-4410",
        "email": "parking@boston.gov",
        "source_url": "https://www.boston.gov/departments/parking-clerk",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"o": office_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    office = await graph_service.get_office_by_id("boston_parking_clerk")

    # Assert
    assert office is not None
    assert isinstance(office, Office)
    assert office.office_id == "boston_parking_clerk"
    assert office.phone == "617-635-4410"


@pytest.mark.asyncio
async def test_get_step_office(graph_service, mock_neo4j_client):
    """Test retrieval of the office for a step."""
    office_data = {
        "office_id": "boston_parking_clerk",
        "name": "Boston Parking Clerk",
        "address": "1 City Hall Square, Room 224, Boston, MA 02201",
        "room": "224",
        "hours": "Mon-Fri, 9:00-4:30",
        "phone": "617-635-4410",
        "email": "parking@boston.gov",
        "source_url": "https://www.boston.gov/departments/parking-clerk",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"o": office_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    office = await graph_service.get_step_office("rpp_step_3_submit_application")

    # Assert
    assert office is not None
    assert office.office_id == "boston_parking_clerk"


# ==================== Rule Query Tests ====================


@pytest.mark.asyncio
async def test_get_rule_by_id(graph_service, mock_neo4j_client):
    """Test retrieval of a rule by ID."""
    rule_data = {
        "rule_id": "rule_rpp.eligibility.vehicle_class",
        "text": "Vehicle must be passenger vehicle or motorcycle",
        "fact_id": "rpp.eligibility.vehicle_class",
        "scope": "general",
        "source_section": "Eligibility Requirements",
        "effective_date": date(2024, 1, 1),
        "source_url": "https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"r": rule_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    rule = await graph_service.get_rule_by_id("rule_rpp.eligibility.vehicle_class")

    # Assert
    assert rule is not None
    assert isinstance(rule, Rule)
    assert rule.rule_id == "rule_rpp.eligibility.vehicle_class"
    assert rule.scope == "general"


@pytest.mark.asyncio
async def test_get_requirement_rules(graph_service, mock_neo4j_client):
    """Test retrieval of rules that govern a requirement."""
    rule_data = {
        "rule_id": "rule_rpp.eligibility.vehicle_class",
        "text": "Vehicle must be passenger vehicle or motorcycle",
        "fact_id": "rpp.eligibility.vehicle_class",
        "scope": "general",
        "source_section": "Eligibility Requirements",
        "effective_date": date(2024, 1, 1),
        "source_url": "https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"r": rule_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    rules = await graph_service.get_requirement_rules("req_vehicle_class")

    # Assert
    assert len(rules) == 1
    assert rules[0].rule_id == "rule_rpp.eligibility.vehicle_class"


# ==================== DAG Query Tests ====================


@pytest.mark.asyncio
async def test_get_process_dag(graph_service, mock_neo4j_client, sample_step_data):
    """Test retrieval of the process DAG for visualization."""
    # Create steps
    step_1 = sample_step_data.copy()
    step_2 = sample_step_data.copy()
    step_2["step_id"] = "rpp_step_2_gather_documents"
    step_2["name"] = "Gather Documents"
    step_2["order"] = 2

    # Mock get_process_steps call
    mock_session = AsyncMock()

    # First call: get steps
    steps_result = AsyncMock()
    steps_result.data = AsyncMock(return_value=[{"s": step_1}, {"s": step_2}])

    # Second call: get edges
    edges_result = AsyncMock()
    edges_result.data = AsyncMock(
        return_value=[
            {
                "source": "rpp_step_2_gather_documents",
                "target": "rpp_step_1_check_eligibility",
                "rel_type": "DEPENDS_ON",
            }
        ]
    )

    # Mock run to return different results for different queries
    mock_session.run = AsyncMock(side_effect=[steps_result, edges_result])
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    dag = await graph_service.get_process_dag("boston_resident_parking_permit")

    # Assert
    assert "nodes" in dag
    assert "edges" in dag
    assert len(dag["nodes"]) == 2
    assert len(dag["edges"]) == 1
    assert dag["nodes"][0]["id"] == "rpp_step_1_check_eligibility"
    assert dag["edges"][0]["source"] == "rpp_step_2_gather_documents"
    assert dag["edges"][0]["target"] == "rpp_step_1_check_eligibility"


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
async def test_execute_query_error_handling(graph_service, mock_neo4j_client):
    """Test error handling in _execute_query."""
    from neo4j.exceptions import Neo4jError

    # Mock a Neo4j error
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Database error"))
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute and expect error
    with pytest.raises(GraphServiceError) as exc_info:
        await graph_service.get_process_by_id("test")

    assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_query_connection_error(graph_service, mock_neo4j_client):
    """Test connection error handling in _execute_query."""
    from neo4j.exceptions import ServiceUnavailable

    # Mock a connection error
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=ServiceUnavailable("Connection refused"))
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute and expect ConnectionError
    with pytest.raises(ConnectionError) as exc_info:
        await graph_service.get_process_by_id("test")

    assert "Database connection failed" in str(exc_info.value)
    assert "Connection refused" in str(exc_info.value)


# ==================== Health Check Tests ====================


@pytest.mark.asyncio
async def test_health_check_success(graph_service, mock_neo4j_client):
    """Test successful health check."""
    mock_neo4j_client.health_check = AsyncMock(
        return_value={"status": "healthy", "details": {"uri": "bolt://localhost:7687"}}
    )

    # Execute
    health = await graph_service.health_check()

    # Assert
    assert health["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_failure(graph_service, mock_neo4j_client):
    """Test health check failure."""
    mock_neo4j_client.health_check = AsyncMock(side_effect=Exception("Connection failed"))

    # Execute
    health = await graph_service.health_check()

    # Assert
    assert health["status"] == "unhealthy"
    assert "Connection failed" in health["error"]


# ==================== Factory Function Tests ====================


def test_get_graph_service_with_client(mock_neo4j_client):
    """Test factory function with provided client."""
    service = get_graph_service(mock_neo4j_client)

    assert isinstance(service, GraphService)
    assert service.client == mock_neo4j_client


def test_get_graph_service_without_client():
    """Test factory function without provided client (creates new one)."""
    with patch("src.db.graph.client.get_neo4j_client") as mock_get_client:
        mock_client = MagicMock(spec=Neo4jClient)
        mock_get_client.return_value = mock_client

        service = get_graph_service()

        assert isinstance(service, GraphService)
        mock_get_client.assert_called_once()


# ==================== RPP Neighborhood Tests ====================


@pytest.mark.asyncio
async def test_get_rpp_neighborhood_by_id(graph_service, mock_neo4j_client):
    """Test retrieval of an RPP neighborhood by ID."""
    nbrhd_data = {
        "nbrhd_id": "back_bay",
        "name": "Back Bay",
        "auto_renew_cycle": date(2025, 12, 1),
        "posted_streets": ["Beacon Street", "Commonwealth Avenue"],
        "notes": "High demand area",
        "source_url": "https://www.boston.gov/departments/parking-clerk",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"n": nbrhd_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    neighborhood = await graph_service.get_rpp_neighborhood_by_id("back_bay")

    # Assert
    assert neighborhood is not None
    assert isinstance(neighborhood, RPPNeighborhood)
    assert neighborhood.nbrhd_id == "back_bay"
    assert neighborhood.name == "Back Bay"


@pytest.mark.asyncio
async def test_get_process_neighborhoods(graph_service, mock_neo4j_client):
    """Test retrieval of neighborhoods for a process."""
    # Sample neighborhood data
    nbrhd_1 = {
        "nbrhd_id": "back_bay",
        "name": "Back Bay",
        "auto_renew_cycle": date(2025, 12, 1),
        "posted_streets": ["Beacon Street", "Commonwealth Avenue"],
        "notes": "High demand area",
        "source_url": "https://www.boston.gov/departments/parking-clerk",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    nbrhd_2 = {
        "nbrhd_id": "south_end",
        "name": "South End",
        "auto_renew_cycle": date(2025, 12, 1),
        "posted_streets": ["Tremont Street", "Columbus Avenue"],
        "notes": None,
        "source_url": "https://www.boston.gov/departments/parking-clerk",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"n": nbrhd_1}, {"n": nbrhd_2}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    neighborhoods = await graph_service.get_process_neighborhoods("boston_resident_parking_permit")

    # Assert
    assert isinstance(neighborhoods, list)
    assert len(neighborhoods) == 2
    assert all(isinstance(n, RPPNeighborhood) for n in neighborhoods)
    assert neighborhoods[0].nbrhd_id == "back_bay"
    assert neighborhoods[1].nbrhd_id == "south_end"
    assert neighborhoods[0].posted_streets == ["Beacon Street", "Commonwealth Avenue"]


@pytest.mark.asyncio
async def test_get_requirement_document_types(graph_service, mock_neo4j_client):
    """Test retrieval of document types that satisfy a requirement."""
    # Mock the session and result
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    # Sample document type data
    sample_doc_type_data = {
        "doc_type_id": "proof.utility_bill",
        "name": "Utility Bill",
        "freshness_days": 30,
        "name_match_required": True,
        "address_match_required": True,
        "examples": ["National Grid", "Eversource"],
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_result.data = AsyncMock(return_value=[{"dt": sample_doc_type_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    doc_types = await graph_service.get_requirement_document_types("req_proof_of_residency")

    # Assert
    assert isinstance(doc_types, list)
    assert len(doc_types) == 1
    assert isinstance(doc_types[0], DocumentType)
    assert doc_types[0].doc_type_id == "proof.utility_bill"
    assert doc_types[0].name == "Utility Bill"
    assert doc_types[0].freshness_days == 30
    assert doc_types[0].name_match_required is True
    assert doc_types[0].address_match_required is True


# ==================== Input Validation Tests ====================


@pytest.mark.parametrize(
    "invalid_id",
    [
        "",  # Empty string
        "   ",  # Whitespace only
        "'; DROP TABLE processes; --",  # SQL injection attempt
        "<script>alert('xss')</script>",  # XSS attempt
    ],
)
@pytest.mark.asyncio
async def test_get_process_by_id_with_invalid_input(graph_service, mock_neo4j_client, invalid_id):
    """Test that invalid inputs are handled gracefully."""
    # Mock setup
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])  # No results
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    process = await graph_service.get_process_by_id(invalid_id)

    # Assert - should return None (not found) without errors
    # The service uses parameterized queries so injection attempts are safe
    assert process is None

    # Verify the query was still executed (parameterized, so safe)
    mock_session.run.assert_called_once()


@pytest.mark.parametrize(
    "invalid_id",
    [
        "",  # Empty string
        "   ",  # Whitespace only
        "'; DROP TABLE steps; --",  # SQL injection attempt
    ],
)
@pytest.mark.asyncio
async def test_get_step_by_id_with_invalid_input(graph_service, mock_neo4j_client, invalid_id):
    """Test that invalid inputs are handled gracefully for step queries."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    step = await graph_service.get_step_by_id(invalid_id)

    # Assert
    assert step is None
    mock_session.run.assert_called_once()


@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        "   ",
        "<img src=x onerror=alert(1)>",
    ],
)
@pytest.mark.asyncio
async def test_get_requirement_by_id_with_invalid_input(
    graph_service, mock_neo4j_client, invalid_id
):
    """Test that invalid inputs are handled gracefully for requirement queries."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    requirement = await graph_service.get_requirement_by_id(invalid_id)

    # Assert
    assert requirement is None
    mock_session.run.assert_called_once()


# ==================== Query Verification Tests ====================


@pytest.mark.asyncio
async def test_get_process_by_id_query_verification(
    graph_service, mock_neo4j_client, sample_process_data
):
    """Test that correct Cypher query is executed with correct parameters."""
    # Mock setup
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    mock_result.data = AsyncMock(return_value=[{"p": sample_process_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    await graph_service.get_process_by_id("test_process")

    # Verify mock was called
    mock_session.run.assert_called_once()

    # Verify query parameters
    call_args = mock_session.run.call_args
    query = call_args[0][0]  # First positional argument
    params = call_args[0][1]  # Second positional argument

    # Verify the query contains expected patterns
    assert "MATCH" in query
    assert "Process" in query
    assert "process_id" in query

    # Verify parameters are passed correctly
    assert params == {"process_id": "test_process"}


@pytest.mark.asyncio
async def test_get_process_steps_query_verification(
    graph_service, mock_neo4j_client, sample_step_data
):
    """Test that correct Cypher query is executed for process steps."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"s": sample_step_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    await graph_service.get_process_steps("test_process")

    # Verify mock was called
    mock_session.run.assert_called_once()

    # Verify query
    call_args = mock_session.run.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    # Verify query structure
    assert "MATCH" in query
    assert "HAS_STEP" in query
    assert "ORDER BY" in query
    assert params == {"process_id": "test_process"}


@pytest.mark.asyncio
async def test_get_requirement_document_types_query_verification(graph_service, mock_neo4j_client):
    """Test that correct Cypher query is executed for requirement document types."""
    doc_type_data = {
        "doc_type_id": "proof.utility_bill",
        "name": "Utility Bill",
        "freshness_days": 30,
        "name_match_required": True,
        "address_match_required": True,
        "examples": [],
        "source_url": "https://example.com",
        "last_verified": date(2025, 11, 9),
        "confidence": "high",
        "created_at": datetime(2025, 11, 9, 12, 0, 0),
        "updated_at": datetime(2025, 11, 9, 12, 0, 0),
    }

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"dt": doc_type_data}])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    await graph_service.get_requirement_document_types("req_residency")

    # Verify mock was called
    mock_session.run.assert_called_once()

    # Verify query
    call_args = mock_session.run.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    # Verify query structure
    assert "MATCH" in query
    assert "SATISFIES" in query
    assert "Requirement" in query
    assert params == {"requirement_id": "req_residency"}


# ==================== Data Conversion Tests ====================


def test_node_to_dict_with_none(graph_service):
    """Test that _node_to_dict handles None gracefully."""
    result = graph_service._node_to_dict(None)
    assert result == {}


def test_node_to_dict_with_dict():
    """Test that _node_to_dict converts node-like objects to dicts."""
    # Create a mock Neo4j node with dict behavior
    mock_node = {"key": "value", "number": 123}
    service = GraphService(MagicMock(spec=Neo4jClient))

    result = service._node_to_dict(mock_node)
    assert isinstance(result, dict)
    assert "key" in result


def test_convert_neo4j_types_with_native_types():
    """Test conversion of Neo4j types to Python types."""
    service = GraphService(MagicMock(spec=Neo4jClient))

    # Test with standard Python types
    data = {
        "string": "test",
        "number": 123,
        "date": date(2025, 11, 9),
        "datetime": datetime(2025, 11, 9, 12, 0, 0),
        "bool": True,
    }

    result = service._convert_neo4j_types(data)

    assert result["string"] == "test"
    assert result["number"] == 123
    assert result["date"] == date(2025, 11, 9)
    assert result["datetime"] == datetime(2025, 11, 9, 12, 0, 0)
    assert result["bool"] is True


def test_convert_neo4j_types_with_to_native():
    """Test conversion of objects with to_native method."""
    service = GraphService(MagicMock(spec=Neo4jClient))

    # Create a mock Neo4j object with to_native method
    class MockNeo4jDate:
        def to_native(self):
            return date(2025, 11, 9)

    data = {"neo4j_date": MockNeo4jDate()}
    result = service._convert_neo4j_types(data)

    assert result["neo4j_date"] == date(2025, 11, 9)


# ==================== Empty Result Tests ====================


@pytest.mark.asyncio
async def test_get_step_dependencies_empty_result(graph_service, mock_neo4j_client):
    """Test retrieval of step dependencies when there are none."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    dependencies = await graph_service.get_step_dependencies("step_with_no_deps")

    # Assert
    assert isinstance(dependencies, list)
    assert len(dependencies) == 0


@pytest.mark.asyncio
async def test_get_process_neighborhoods_empty_result(graph_service, mock_neo4j_client):
    """Test retrieval of neighborhoods when process has none."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    neighborhoods = await graph_service.get_process_neighborhoods("process_no_neighborhoods")

    # Assert
    assert isinstance(neighborhoods, list)
    assert len(neighborhoods) == 0


@pytest.mark.asyncio
async def test_get_requirement_document_types_empty_result(graph_service, mock_neo4j_client):
    """Test retrieval of document types when requirement has none."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_neo4j_client.get_session.return_value.__aenter__.return_value = mock_session

    # Execute
    doc_types = await graph_service.get_requirement_document_types("req_no_docs")

    # Assert
    assert isinstance(doc_types, list)
    assert len(doc_types) == 0
