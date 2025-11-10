"""Integration tests for GraphService with real Neo4j database.

These tests require a running Neo4j instance with seeded data.
Run with: pytest -v -m integration

To skip integration tests: pytest -v -m "not integration"
"""

from datetime import date

import pytest

from src.db.graph.client import Neo4jClient
from src.schemas.graph import (
    ConfidenceLevel,
    DocumentType,
    Office,
    Process,
    Requirement,
    Rule,
    Step,
)
from src.services.graph_service import GraphService


@pytest.fixture(scope="module")
async def neo4j_client():
    """
    Create a real Neo4j client for integration tests.

    This fixture requires:
    - Neo4j running (via docker-compose or locally)
    - Database seeded with test data (run scripts/seed_rpp.py)
    """
    client = Neo4jClient()
    await client.connect()

    # Verify connection
    health = await client.health_check()
    if health["status"] != "healthy":
        pytest.skip("Neo4j not available for integration tests")

    yield client

    await client.close()


@pytest.fixture
async def graph_service(neo4j_client):
    """Create a GraphService with real Neo4j connection."""
    return GraphService(neo4j_client)


# ==================== Process Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_process_by_id(graph_service):
    """Integration test: Retrieve a process by ID from real database."""
    process = await graph_service.get_process_by_id("boston_resident_parking_permit")

    assert process is not None
    assert isinstance(process, Process)
    assert process.process_id == "boston_resident_parking_permit"
    assert process.name == "Boston Resident Parking Permit"
    assert process.jurisdiction == "City of Boston"
    assert process.confidence == ConfidenceLevel.HIGH
    assert isinstance(process.last_verified, date)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_process_not_found(graph_service):
    """Integration test: Try to retrieve a non-existent process."""
    process = await graph_service.get_process_by_id("nonexistent_process")

    assert process is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_all_processes(graph_service):
    """Integration test: Retrieve all processes."""
    processes = await graph_service.get_all_processes()

    assert len(processes) > 0
    assert all(isinstance(p, Process) for p in processes)
    # Should include our seeded process
    process_ids = [p.process_id for p in processes]
    assert "boston_resident_parking_permit" in process_ids


# ==================== Step Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_process_steps(graph_service):
    """Integration test: Retrieve all steps for a process."""
    steps = await graph_service.get_process_steps("boston_resident_parking_permit")

    assert len(steps) >= 3  # Should have at least 3 steps from seed data
    assert all(isinstance(s, Step) for s in steps)

    # Verify ordering
    for i in range(len(steps) - 1):
        assert steps[i].order < steps[i + 1].order

    # Check specific steps exist
    step_ids = [s.step_id for s in steps]
    assert "rpp_step_1_check_eligibility" in step_ids
    assert "rpp_step_2_gather_documents" in step_ids
    assert "rpp_step_3_submit_application" in step_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_step_by_id(graph_service):
    """Integration test: Retrieve a specific step."""
    step = await graph_service.get_step_by_id("rpp_step_1_check_eligibility")

    assert step is not None
    assert isinstance(step, Step)
    assert step.step_id == "rpp_step_1_check_eligibility"
    assert step.process_id == "boston_resident_parking_permit"
    assert step.order == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_step_dependencies(graph_service):
    """Integration test: Retrieve dependencies for a step."""
    # Step 2 should depend on Step 1
    dependencies = await graph_service.get_step_dependencies("rpp_step_2_gather_documents")

    assert len(dependencies) >= 1
    assert all(isinstance(d, Step) for d in dependencies)
    # Step 1 should be a dependency
    dep_ids = [d.step_id for d in dependencies]
    assert "rpp_step_1_check_eligibility" in dep_ids


# ==================== Requirement Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_process_requirements(graph_service):
    """Integration test: Retrieve all requirements for a process."""
    requirements = await graph_service.get_process_requirements("boston_resident_parking_permit")

    assert len(requirements) > 0
    assert all(isinstance(r, Requirement) for r in requirements)

    # Check that we have expected requirements
    req_ids = [r.requirement_id for r in requirements]
    assert "req_residency_proof" in req_ids or "req_vehicle_registration" in req_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_requirement_by_id(graph_service):
    """Integration test: Retrieve a specific requirement."""
    requirement = await graph_service.get_requirement_by_id("req_residency_proof")

    if requirement:  # May not exist depending on seed data
        assert isinstance(requirement, Requirement)
        assert requirement.requirement_id == "req_residency_proof"
        assert requirement.applies_to_process == "boston_resident_parking_permit"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_hard_gate_requirements(graph_service):
    """Integration test: Retrieve hard-gate requirements."""
    requirements = await graph_service.get_hard_gate_requirements("boston_resident_parking_permit")

    # Should have at least some hard-gate requirements
    assert all(isinstance(r, Requirement) for r in requirements)
    assert all(r.hard_gate is True for r in requirements)


# ==================== Document Type Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_step_document_types(graph_service):
    """Integration test: Retrieve document types for a step."""
    doc_types = await graph_service.get_step_document_types("rpp_step_2_gather_documents")

    assert len(doc_types) > 0
    assert all(isinstance(dt, DocumentType) for dt in doc_types)

    # Should include common document types
    doc_type_ids = [dt.doc_type_id for dt in doc_types]
    # Check for at least one expected document type
    assert any("proof." in dt_id for dt_id in doc_type_ids)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_document_type_by_id(graph_service):
    """Integration test: Retrieve a specific document type."""
    doc_type = await graph_service.get_document_type_by_id("proof.utility_bill")

    if doc_type:  # May not exist depending on seed data
        assert isinstance(doc_type, DocumentType)
        assert doc_type.doc_type_id == "proof.utility_bill"
        assert doc_type.freshness_days == 30


# ==================== Office Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_office_by_id(graph_service):
    """Integration test: Retrieve an office."""
    office = await graph_service.get_office_by_id("boston_parking_clerk")

    assert office is not None
    assert isinstance(office, Office)
    assert office.office_id == "boston_parking_clerk"
    assert "Boston" in office.name or "Parking" in office.name
    assert office.address is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_step_office(graph_service):
    """Integration test: Retrieve the office for a step."""
    # Step 3 (submit application) should have an office
    office = await graph_service.get_step_office("rpp_step_3_submit_application")

    if office:  # May not exist depending on seed data
        assert isinstance(office, Office)
        assert office.office_id == "boston_parking_clerk"


# ==================== Rule Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_requirement_rules(graph_service):
    """Integration test: Retrieve rules for a requirement."""
    # First get a requirement
    requirements = await graph_service.get_process_requirements("boston_resident_parking_permit")

    if requirements:
        # Get rules for the first requirement
        rules = await graph_service.get_requirement_rules(requirements[0].requirement_id)

        # Rules may or may not exist depending on relationships
        assert all(isinstance(r, Rule) for r in rules)


# ==================== DAG Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_get_process_dag(graph_service):
    """Integration test: Retrieve the complete process DAG."""
    dag = await graph_service.get_process_dag("boston_resident_parking_permit")

    assert "nodes" in dag
    assert "edges" in dag

    # Should have multiple nodes (steps)
    assert len(dag["nodes"]) >= 3

    # Each node should have expected structure
    for node in dag["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "order" in node
        assert "data" in node

    # Should have edges (dependencies)
    # At least step 2 depends on step 1, and step 3 depends on step 2
    for edge in dag["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge

    # Verify specific dependencies
    edge_pairs = [(e["source"], e["target"]) for e in dag["edges"]]
    # Step 2 should depend on step 1
    assert (
        "rpp_step_2_gather_documents",
        "rpp_step_1_check_eligibility",
    ) in edge_pairs or (
        "rpp_step_3_submit_application",
        "rpp_step_2_gather_documents",
    ) in edge_pairs


# ==================== Health Check Integration Test ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_health_check(graph_service):
    """Integration test: Verify health check works with real database."""
    health = await graph_service.health_check()

    assert health["status"] == "healthy"
    assert "details" in health


# ==================== Edge Cases Integration Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_empty_result_handling(graph_service):
    """Integration test: Handle queries that return no results."""
    # Query for a process that doesn't exist
    process = await graph_service.get_process_by_id("definitely_not_a_real_process_12345")
    assert process is None

    # Query for steps of a non-existent process
    steps = await graph_service.get_process_steps("definitely_not_a_real_process_12345")
    assert steps == []

    # Query for requirements of a non-existent process
    requirements = await graph_service.get_process_requirements(
        "definitely_not_a_real_process_12345"
    )
    assert requirements == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_step_without_dependencies(graph_service):
    """Integration test: Handle steps with no dependencies."""
    # Step 1 should have no dependencies
    dependencies = await graph_service.get_step_dependencies("rpp_step_1_check_eligibility")

    # Should return empty list, not error
    assert dependencies == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_step_without_office(graph_service):
    """Integration test: Handle steps without an office."""
    # Step 1 (check eligibility) probably doesn't have an office
    office = await graph_service.get_step_office("rpp_step_1_check_eligibility")

    # Should return None, not error
    assert office is None
