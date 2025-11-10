"""Facts Registry service layer for loading and querying regulatory facts.

This module provides a service layer that loads facts from YAML files,
caches them in memory, and provides query methods for accessing facts.
Facts are the citation system that ensures all regulatory claims are
traceable to official sources.

Usage:
    ```python
    from pathlib import Path
    from src.services.facts_service import FactsService

    # Initialize service with facts directory
    facts_dir = Path("docs/facts")
    service = FactsService(facts_dir)

    # Load a registry
    registry = service.load_registry("boston_rpp")

    # Query facts
    fact = service.get_fact_by_id("rpp.eligibility.vehicle_class")
    eligibility_facts = service.get_facts_by_prefix("rpp.eligibility")
    all_facts = service.get_all_facts()
    ```
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any

import yaml
from pydantic import ValidationError

from src.schemas.facts import Fact, FactsRegistry

logger = logging.getLogger(__name__)


class FactsServiceError(Exception):
    """Base exception for facts service errors."""

    pass


class RegistryNotFoundError(FactsServiceError):
    """Raised when a requested registry YAML file is not found."""

    pass


class RegistryParseError(FactsServiceError):
    """Raised when a registry YAML file cannot be parsed."""

    pass


class RegistryValidationError(FactsServiceError):
    """Raised when a registry fails Pydantic validation."""

    pass


class FactsService:
    """
    Service layer for loading and querying the Facts Registry.

    This class provides high-level methods for loading regulatory facts from
    YAML files, caching them in memory, and querying them efficiently.
    Thread-safe for concurrent access.

    Attributes:
        facts_dir: Path to the directory containing facts YAML files
        _cache: In-memory cache of loaded registries (scope -> FactsRegistry)
        _lock: Thread lock for safe concurrent access
    """

    def __init__(self, facts_dir: Path | str) -> None:
        """
        Initialize the facts service.

        Args:
            facts_dir: Path to directory containing facts YAML files
                      (e.g., Path("docs/facts"))
        """
        self.facts_dir = Path(facts_dir)
        self._cache: dict[str, FactsRegistry] = {}
        self._lock = Lock()

        if not self.facts_dir.exists():
            logger.warning(
                f"Facts directory does not exist: {self.facts_dir}. It will be created when needed."
            )
        elif not self.facts_dir.is_dir():
            raise FactsServiceError(f"Facts path is not a directory: {self.facts_dir}")

    def _get_registry_path(self, registry_name: str) -> Path:
        """
        Get the file path for a registry YAML file.

        Args:
            registry_name: Name of the registry (e.g., "boston_rpp")

        Returns:
            Path to the registry YAML file
        """
        return self.facts_dir / f"{registry_name}.yaml"

    def load_registry(self, registry_name: str) -> FactsRegistry:
        """
        Load a facts registry from a YAML file and cache it.

        If the registry is already cached, returns the cached version.
        Use reload_registry() to force a reload from disk.

        Args:
            registry_name: Name of the registry file without extension
                          (e.g., "boston_rpp" for "boston_rpp.yaml")

        Returns:
            FactsRegistry model with all facts loaded

        Raises:
            RegistryNotFoundError: If the YAML file doesn't exist
            RegistryParseError: If the YAML file cannot be parsed
            RegistryValidationError: If the data fails Pydantic validation
        """
        # Use lock for thread-safe cache check and load
        with self._lock:
            # Check cache first (double-check pattern for thread safety)
            if registry_name in self._cache:
                logger.debug(f"Returning cached registry: {registry_name}")
                return self._cache[registry_name]

            # Load from disk (still inside lock to prevent duplicate loads)
            registry_path = self._get_registry_path(registry_name)

            if not registry_path.exists():
                raise RegistryNotFoundError(f"Registry file not found: {registry_path}")

            try:
                with open(registry_path) as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML file {registry_path}: {e}")
                raise RegistryParseError(f"Failed to parse registry YAML: {e}") from e
            except Exception as e:
                logger.error(f"Failed to read file {registry_path}: {e}")
                raise RegistryParseError(f"Failed to read registry file: {e}") from e

            # Validate with Pydantic
            try:
                registry = FactsRegistry(**data)
            except ValidationError as e:
                logger.error(f"Registry validation failed for {registry_name}: {e}")
                raise RegistryValidationError(f"Registry validation failed: {e}") from e

            # Cache and return
            self._cache[registry_name] = registry
            logger.info(f"Loaded registry '{registry_name}' with {len(registry.facts)} facts")

            return registry

    def reload_registry(self, registry_name: str) -> FactsRegistry:
        """
        Force reload a registry from disk, bypassing the cache.

        Use this when you know the YAML file has been updated.

        Args:
            registry_name: Name of the registry to reload

        Returns:
            FactsRegistry model with refreshed data

        Raises:
            RegistryNotFoundError: If the YAML file doesn't exist
            RegistryParseError: If the YAML file cannot be parsed
            RegistryValidationError: If the data fails Pydantic validation
        """
        # Remove from cache if present
        with self._lock:
            if registry_name in self._cache:
                del self._cache[registry_name]
                logger.debug(f"Cleared cache for registry: {registry_name}")

        # Load fresh from disk
        return self.load_registry(registry_name)

    def get_fact_by_id(self, fact_id: str) -> Fact | None:
        """
        Retrieve a specific fact by its ID from all loaded registries.

        Args:
            fact_id: Unique fact identifier (e.g., "rpp.eligibility.vehicle_class")

        Returns:
            Fact model or None if not found
        """
        with self._lock:
            for registry in self._cache.values():
                for fact in registry.facts:
                    if fact.id == fact_id:
                        return fact
        return None

    def get_facts_by_prefix(self, prefix: str) -> list[Fact]:
        """
        Retrieve all facts whose IDs start with the given prefix.

        This is useful for getting all facts in a category or subcategory.

        Args:
            prefix: ID prefix to match (e.g., "rpp.eligibility" or "rpp.")

        Returns:
            List of matching Fact models (may be empty)

        Examples:
            ```python
            # Get all eligibility facts
            eligibility = service.get_facts_by_prefix("rpp.eligibility")

            # Get all RPP facts
            rpp_facts = service.get_facts_by_prefix("rpp.")
            ```
        """
        matching_facts: list[Fact] = []
        with self._lock:
            for registry in self._cache.values():
                for fact in registry.facts:
                    if fact.id.startswith(prefix):
                        matching_facts.append(fact)
        return matching_facts

    def get_all_facts(self) -> list[Fact]:
        """
        Retrieve all facts from all loaded registries.

        Returns:
            List of all Fact models from all cached registries
        """
        all_facts: list[Fact] = []
        with self._lock:
            for registry in self._cache.values():
                all_facts.extend(registry.facts)
        return all_facts

    def get_registry_info(self, registry_name: str) -> dict[str, Any]:
        """
        Get metadata about a loaded registry.

        Args:
            registry_name: Name of the registry

        Returns:
            Dictionary with registry metadata (version, scope, last_updated, fact_count)
            Returns None if registry is not loaded

        Raises:
            FactsServiceError: If registry is not loaded
        """
        with self._lock:
            if registry_name not in self._cache:
                raise FactsServiceError(
                    f"Registry '{registry_name}' is not loaded. "
                    f"Call load_registry('{registry_name}') first."
                )

            registry = self._cache[registry_name]
            return {
                "registry_name": registry_name,
                "version": registry.version,
                "scope": registry.scope,
                "last_updated": registry.last_updated.isoformat(),
                "fact_count": len(registry.facts),
            }

    def get_loaded_registries(self) -> list[str]:
        """
        Get the names of all currently loaded registries.

        Returns:
            List of registry names that are cached
        """
        with self._lock:
            return list(self._cache.keys())

    def clear_cache(self) -> None:
        """
        Clear all cached registries.

        Use this to free memory or force fresh loads on next access.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} registries from cache")


def get_facts_service(facts_dir: Path | str | None = None) -> FactsService:
    """
    Factory function to create a FactsService instance.

    This is useful for dependency injection in FastAPI routes.

    Args:
        facts_dir: Optional directory path. If None, uses default "docs/facts"

    Returns:
        FactsService instance

    Example:
        ```python
        from fastapi import Depends
        from src.services.facts_service import get_facts_service, FactsService

        @app.get("/facts/{fact_id}")
        async def get_fact(
            fact_id: str,
            service: FactsService = Depends(get_facts_service)
        ):
            fact = service.get_fact_by_id(fact_id)
            if not fact:
                raise HTTPException(status_code=404, detail="Fact not found")
            return fact
        ```
    """
    if facts_dir is None:
        # Default to docs/facts relative to project root
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent.parent
        facts_dir = project_root / "docs" / "facts"

    return FactsService(facts_dir)
