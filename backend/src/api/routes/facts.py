"""REST API endpoints for Facts Registry.

This module provides endpoints for:
- Listing all facts (optionally filtered by registry)
- Getting a specific fact by ID
- Searching facts by ID prefix
- Listing available registries
- Getting registry metadata
- Loading registries on-demand

All endpoints use the FactsService for querying regulatory facts with citations.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.schemas.facts import Fact
from src.services.facts_service import (
    FactsService,
    FactsServiceError,
    RegistryNotFoundError,
    RegistryParseError,
    RegistryValidationError,
    get_facts_service,
)


def get_facts_service_dependency() -> FactsService:
    """
    Dependency function to get a FactsService instance.

    This is a wrapper around get_facts_service that works with FastAPI's
    dependency injection system.

    Returns:
        FactsService instance configured with default facts directory
    """
    return get_facts_service()


# Create router with prefix and tags
router = APIRouter(prefix="/api/facts", tags=["facts"])

# Create router for registry management
registries_router = APIRouter(prefix="/api/registries", tags=["registries"])


@router.get("/", response_model=list[Fact])
async def list_facts(
    registry_name: str | None = Query(
        default=None,
        description="Optional registry name to filter facts (e.g., 'boston_rpp')",
    ),
    service: FactsService = Depends(get_facts_service_dependency),
) -> list[Fact]:
    """
    List all facts, optionally filtered by registry name.

    If registry_name is provided, only facts from that registry are returned.
    Otherwise, all facts from all loaded registries are returned.

    Args:
        registry_name: Optional registry name to filter by
        service: FactsService instance (injected)

    Returns:
        List of Fact models

    Raises:
        HTTPException: 404 if registry not found, 500 if service error occurs

    Examples:
        - GET /api/facts - Get all facts from all loaded registries
        - GET /api/facts?registry_name=boston_rpp - Get facts from boston_rpp registry only
    """
    try:
        if registry_name:
            # Load the registry if not already cached
            registry = service.load_registry(registry_name)
            return registry.facts
        else:
            # Return all facts from all loaded registries
            return service.get_all_facts()
    except RegistryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry '{registry_name}' not found: {str(e)}",
        ) from e
    except (RegistryParseError, RegistryValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading registry '{registry_name}': {str(e)}",
        ) from e
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving facts: {str(e)}",
        ) from e


@router.get("/search", response_model=list[Fact])
async def search_facts(
    prefix: str = Query(
        ...,
        min_length=1,
        description="ID prefix to search for (e.g., 'rpp.eligibility')",
    ),
    service: FactsService = Depends(get_facts_service_dependency),
) -> list[Fact]:
    """
    Search for facts whose IDs start with the given prefix.

    This is useful for finding all facts in a category or subcategory.

    Args:
        prefix: ID prefix to match (e.g., "rpp.eligibility" or "rpp.")
        service: FactsService instance (injected)

    Returns:
        List of matching Fact models (may be empty if no matches)

    Raises:
        HTTPException: 500 if service error occurs

    Examples:
        - GET /api/facts/search?prefix=rpp.eligibility - Get all eligibility facts
        - GET /api/facts/search?prefix=rpp. - Get all RPP facts
    """
    try:
        facts = service.get_facts_by_prefix(prefix)
        return facts
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching facts: {str(e)}",
        ) from e


@router.get("/{fact_id}", response_model=Fact)
async def get_fact(
    fact_id: str,
    service: FactsService = Depends(get_facts_service_dependency),
) -> Fact:
    """
    Get a specific fact by its ID.

    Args:
        fact_id: Unique fact identifier (e.g., "rpp.eligibility.vehicle_class")
        service: FactsService instance (injected)

    Returns:
        Fact model with full citation details

    Raises:
        HTTPException: 404 if fact not found, 500 if service error occurs

    Examples:
        - GET /api/facts/rpp.eligibility.vehicle_class
    """
    try:
        fact = service.get_fact_by_id(fact_id)
        if not fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fact '{fact_id}' not found",
            )
        return fact
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving fact: {str(e)}",
        ) from e


@registries_router.get("/", response_model=list[str])
async def list_registries(
    service: FactsService = Depends(get_facts_service_dependency),
) -> list[str]:
    """
    List all currently loaded registries.

    Returns the names of registries that have been loaded into the service cache.

    Args:
        service: FactsService instance (injected)

    Returns:
        List of registry names (e.g., ["boston_rpp"])

    Raises:
        HTTPException: 500 if service error occurs

    Examples:
        - GET /api/registries
    """
    try:
        registries = service.get_loaded_registries()
        return registries
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving registries: {str(e)}",
        ) from e


@registries_router.get("/{registry_name}", response_model=dict[str, Any])
async def get_registry_metadata(
    registry_name: str,
    service: FactsService = Depends(get_facts_service_dependency),
) -> dict[str, Any]:
    """
    Get metadata about a specific registry.

    Returns information about the registry including version, scope, last updated,
    and fact count.

    Args:
        registry_name: Name of the registry (e.g., "boston_rpp")
        service: FactsService instance (injected)

    Returns:
        Dictionary with registry metadata:
        ```json
        {
            "registry_name": "boston_rpp",
            "version": "1.0.0",
            "scope": "boston_resident_parking_permit",
            "last_updated": "2025-11-09",
            "fact_count": 15
        }
        ```

    Raises:
        HTTPException: 404 if registry not found or not loaded, 500 if service error

    Examples:
        - GET /api/registries/boston_rpp
    """
    try:
        # Try to load the registry if not already cached
        service.load_registry(registry_name)
        # Get metadata
        metadata = service.get_registry_info(registry_name)
        return metadata
    except RegistryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry '{registry_name}' not found: {str(e)}",
        ) from e
    except (RegistryParseError, RegistryValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading registry '{registry_name}': {str(e)}",
        ) from e
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving registry metadata: {str(e)}",
        ) from e


@registries_router.post("/{registry_name}/load", response_model=dict[str, Any])
async def load_registry(
    registry_name: str,
    reload: bool = Query(
        default=False,
        description="If true, force reload from disk even if already cached",
    ),
    service: FactsService = Depends(get_facts_service_dependency),
) -> dict[str, Any]:
    """
    Load a registry into the service cache.

    This endpoint allows on-demand loading of registries. Use the reload parameter
    to force a fresh load from disk if the YAML file has been updated.

    Args:
        registry_name: Name of the registry to load (e.g., "boston_rpp")
        reload: If true, force reload from disk (default: false)
        service: FactsService instance (injected)

    Returns:
        Dictionary with load confirmation and registry metadata

    Raises:
        HTTPException: 404 if registry not found, 500 if parse/validation error

    Examples:
        - POST /api/registries/boston_rpp/load
        - POST /api/registries/boston_rpp/load?reload=true
    """
    try:
        if reload:
            registry = service.reload_registry(registry_name)
        else:
            registry = service.load_registry(registry_name)

        return {
            "status": "loaded" if not reload else "reloaded",
            "registry_name": registry_name,
            "version": registry.version,
            "scope": registry.scope,
            "last_updated": registry.last_updated.isoformat(),
            "fact_count": len(registry.facts),
        }
    except RegistryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry '{registry_name}' not found: {str(e)}",
        ) from e
    except (RegistryParseError, RegistryValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading registry '{registry_name}': {str(e)}",
        ) from e
    except FactsServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading registry: {str(e)}",
        ) from e
