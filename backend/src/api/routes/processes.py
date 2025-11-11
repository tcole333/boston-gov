"""REST API endpoints for process navigation and details.

This module provides endpoints for:
- Listing all processes
- Getting process details
- Retrieving process steps
- Getting step details
- Accessing process DAG for visualization
- Fetching process requirements

All endpoints use the GraphService for querying Neo4j and return
Pydantic models defined in src.schemas.graph.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import HttpUrl

from src.db.graph.client import get_neo4j_client
from src.schemas.api import DocumentTypeResponse
from src.schemas.graph import Process, Requirement, Step
from src.services.graph_service import (
    ConnectionError,
    GraphService,
    GraphServiceError,
)


def get_graph_service_dependency() -> GraphService:
    """
    Dependency function to get a GraphService instance.

    This is a wrapper around get_graph_service that works with FastAPI's
    dependency injection system.

    Returns:
        GraphService instance
    """
    client = get_neo4j_client()
    return GraphService(client)


# Create router with prefix and tags
router = APIRouter(prefix="/api/processes", tags=["processes"])


@router.get("/", response_model=list[Process])
async def list_processes(
    service: GraphService = Depends(get_graph_service_dependency),
) -> list[Process]:
    """
    List all available processes.

    Returns a list of all processes in the database, ordered by name.

    Returns:
        List of Process models

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        processes = await service.get_all_processes()
        return processes
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving processes: {str(e)}",
        ) from e


@router.get("/{process_id}", response_model=Process)
async def get_process(
    process_id: str,
    service: GraphService = Depends(get_graph_service_dependency),
) -> Process:
    """
    Get details for a specific process.

    Args:
        process_id: Unique process identifier (e.g., "boston_resident_parking_permit")

    Returns:
        Process model with full details

    Raises:
        HTTPException: 404 if process not found, 500 if database error
    """
    try:
        process = await service.get_process_by_id(process_id)
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process '{process_id}' not found",
            )
        return process
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving process: {str(e)}",
        ) from e


@router.get("/{process_id}/steps", response_model=list[Step])
async def get_process_steps(
    process_id: str,
    service: GraphService = Depends(get_graph_service_dependency),
) -> list[Step]:
    """
    Get all steps for a process, ordered by step order.

    Args:
        process_id: Unique process identifier

    Returns:
        List of Step models ordered by step.order

    Raises:
        HTTPException: 500 if database error occurs

    Note:
        Returns empty list if process has no steps (does not raise 404).
        Use GET /{process_id} to verify process exists.
    """
    try:
        steps = await service.get_process_steps(process_id)
        return steps
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving steps: {str(e)}",
        ) from e


@router.get("/{process_id}/steps/{step_id}", response_model=Step)
async def get_step(
    process_id: str,
    step_id: str,
    service: GraphService = Depends(get_graph_service_dependency),
) -> Step:
    """
    Get details for a specific step.

    Args:
        process_id: Process identifier (for URL structure, not validated)
        step_id: Unique step identifier (e.g., "rpp_step_1_check_eligibility")

    Returns:
        Step model with full details

    Raises:
        HTTPException: 404 if step not found, 500 if database error

    Note:
        The process_id in the URL is for REST structure only.
        The step is looked up by step_id alone, which is globally unique.
    """
    try:
        step = await service.get_step_by_id(step_id)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Step '{step_id}' not found",
            )
        return step
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving step: {str(e)}",
        ) from e


@router.get("/{process_id}/dag", response_model=dict[str, Any])
async def get_process_dag(
    process_id: str,
    service: GraphService = Depends(get_graph_service_dependency),
) -> dict[str, Any]:
    """
    Get the process DAG (Directed Acyclic Graph) for visualization.

    Returns nodes (steps) and edges (dependencies) suitable for rendering
    in a frontend visualization library like D3.js or Cytoscape.js.

    Args:
        process_id: Unique process identifier

    Returns:
        Dictionary with structure:
        ```json
        {
            "nodes": [
                {
                    "id": "step_id",
                    "label": "step name",
                    "order": 1,
                    "data": {...}
                }
            ],
            "edges": [
                {
                    "source": "step_1",
                    "target": "step_2",
                    "type": "DEPENDS_ON"
                }
            ]
        }
        ```

    Raises:
        HTTPException: 500 if database error occurs

    Note:
        Returns empty nodes/edges arrays if process has no steps.
    """
    try:
        dag = await service.get_process_dag(process_id)
        return dag
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving DAG: {str(e)}",
        ) from e


@router.get("/{process_id}/requirements", response_model=list[Requirement])
async def get_process_requirements(
    process_id: str,
    service: GraphService = Depends(get_graph_service_dependency),
) -> list[Requirement]:
    """
    Get all requirements for a process.

    Args:
        process_id: Unique process identifier

    Returns:
        List of Requirement models

    Raises:
        HTTPException: 500 if database error occurs

    Note:
        Returns empty list if process has no requirements (does not raise 404).
        Use GET /{process_id} to verify process exists.
    """
    try:
        requirements = await service.get_process_requirements(process_id)
        return requirements
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
    except GraphServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving requirements: {str(e)}",
        ) from e


@router.get("/{process_id}/document-types", response_model=list[DocumentTypeResponse])
async def get_process_document_types(
    process_id: str,
) -> list[DocumentTypeResponse]:
    """
    Get document types required for a process.

    Returns metadata about each document type including accepted formats,
    size limits, and citations to official sources.

    Args:
        process_id: Unique process identifier (e.g., "boston_resident_parking_permit")

    Returns:
        List of DocumentTypeResponse models with citation metadata

    Raises:
        HTTPException: None - returns empty list for unknown processes

    Note:
        For MVP: Returns hardcoded Boston RPP document types sourced from
        docs/facts/boston_rpp.yaml. Future versions will query Neo4j for
        dynamic requirements per process.

        All document types include regulatory citations:
        - source_url: Official Boston.gov page
        - source_section: Specific section on page
        - last_verified: Date requirement was verified (YYYY-MM-DD)
        - confidence: "high" | "medium" | "low"
    """
    # MVP: Hardcoded for Boston RPP
    # Source: docs/facts/boston_rpp.yaml
    # See facts: rpp.proof_of_residency.accepted_types (lines 54-59)
    if process_id == "boston_resident_parking_permit":
        # Base URL for all Boston RPP document citations
        base_url = HttpUrl(
            "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"
        )

        return [
            DocumentTypeResponse(
                id="proof_of_residency",
                label="Proof of Boston Residency",
                description="Document proving you live in Boston. Accepted: utility bill (gas/electric/telephone), cable bill, bank statement, mortgage statement, credit card statement, water/sewer bill, or lease agreement. Must be dated within 30 days and name must match registration.",
                accepted_formats=["pdf", "jpg", "jpeg", "png"],
                max_size_mb=10,
                required=True,
                source_url=base_url,
                source_section="Proof of Boston residency",
                last_verified="2025-11-09",
                confidence="high",
            ),
            DocumentTypeResponse(
                id="vehicle_registration",
                label="Vehicle Registration",
                description="Current Massachusetts vehicle registration in your name at the Boston address, with principal garaging and insurance at that address. No unpaid Boston parking tickets allowed on the registration.",
                accepted_formats=["pdf", "jpg", "jpeg", "png"],
                max_size_mb=10,
                required=True,
                source_url=base_url,
                source_section="Proof of vehicle ownership",
                last_verified="2025-11-09",
                confidence="high",
            ),
        ]

    # For other processes, return empty list (to be implemented)
    return []
