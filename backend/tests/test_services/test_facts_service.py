"""Unit tests for FactsService with mocked file operations.

These tests use pytest and mocks to verify that the FactsService correctly
loads YAML files, caches them, and provides query methods.
"""

import pytest
import yaml

from src.schemas.facts import Fact, FactsRegistry
from src.schemas.graph import ConfidenceLevel
from src.services.facts_service import (
    FactsService,
    FactsServiceError,
    RegistryNotFoundError,
    RegistryParseError,
    RegistryValidationError,
    get_facts_service,
)


@pytest.fixture
def temp_facts_dir(tmp_path):
    """Create a temporary facts directory for testing."""
    facts_dir = tmp_path / "facts"
    facts_dir.mkdir()
    return facts_dir


@pytest.fixture
def sample_fact_data():
    """Sample fact data for testing."""
    return {
        "id": "rpp.eligibility.vehicle_class",
        "text": "Eligible vehicles are passenger vehicles or commercial vehicles under 1 ton",
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "source_section": "Vehicle eligibility",
        "last_verified": "2025-11-09",
        "confidence": "high",
    }


@pytest.fixture
def sample_registry_data(sample_fact_data):
    """Sample registry data for testing."""
    return {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "boston_resident_parking_permit",
        "facts": [
            sample_fact_data,
            {
                "id": "rpp.eligibility.registration_state",
                "text": "Vehicle must have valid Massachusetts registration",
                "source_url": "https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf",
                "source_section": "Section 15, Rule 15-4A",
                "last_verified": "2025-11-09",
                "confidence": "high",
            },
            {
                "id": "rpp.proof_of_residency.count",
                "text": "Exactly one proof of residency required",
                "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                "source_section": "Proof of Boston residency",
                "last_verified": "2025-11-09",
                "confidence": "high",
            },
        ],
    }


@pytest.fixture
def facts_service(temp_facts_dir):
    """Create a FactsService instance with temporary directory."""
    return FactsService(temp_facts_dir)


# ==================== Initialization Tests ====================


def test_facts_service_initialization_with_valid_dir(temp_facts_dir):
    """Test FactsService initializes with valid directory."""
    service = FactsService(temp_facts_dir)
    assert service.facts_dir == temp_facts_dir
    assert isinstance(service._cache, dict)
    assert len(service._cache) == 0


def test_facts_service_initialization_with_string_path(temp_facts_dir):
    """Test FactsService accepts string path."""
    service = FactsService(str(temp_facts_dir))
    assert service.facts_dir == temp_facts_dir


def test_facts_service_initialization_with_nonexistent_dir(tmp_path):
    """Test FactsService initialization with non-existent directory (warns but doesn't fail)."""
    nonexistent_dir = tmp_path / "nonexistent"
    service = FactsService(nonexistent_dir)
    assert service.facts_dir == nonexistent_dir


def test_facts_service_initialization_with_file_not_dir(tmp_path):
    """Test FactsService raises error if path is a file, not directory."""
    file_path = tmp_path / "not_a_dir.txt"
    file_path.touch()

    with pytest.raises(FactsServiceError, match="not a directory"):
        FactsService(file_path)


# ==================== Registry Loading Tests ====================


def test_load_registry_success(facts_service, sample_registry_data, temp_facts_dir):
    """Test successful registry loading from YAML file."""
    # Create test YAML file
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Load registry
    registry = facts_service.load_registry("boston_rpp")

    # Verify
    assert isinstance(registry, FactsRegistry)
    assert registry.version == "1.0.0"
    assert registry.scope == "boston_resident_parking_permit"
    assert len(registry.facts) == 3
    assert registry.facts[0].id == "rpp.eligibility.vehicle_class"


def test_load_registry_caching(facts_service, sample_registry_data, temp_facts_dir):
    """Test that loaded registries are cached and reused."""
    # Create test YAML file
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Load registry twice
    registry1 = facts_service.load_registry("boston_rpp")
    registry2 = facts_service.load_registry("boston_rpp")

    # Should be the same object (from cache)
    assert registry1 is registry2
    assert len(facts_service._cache) == 1


def test_load_registry_file_not_found(facts_service):
    """Test error when registry file doesn't exist."""
    with pytest.raises(RegistryNotFoundError, match="not found"):
        facts_service.load_registry("nonexistent")


def test_load_registry_invalid_yaml(facts_service, temp_facts_dir):
    """Test error when YAML file is malformed."""
    # Create invalid YAML file
    yaml_file = temp_facts_dir / "bad_yaml.yaml"
    with open(yaml_file, "w") as f:
        f.write("invalid: yaml: content: [[[")

    with pytest.raises(RegistryParseError, match="parse"):
        facts_service.load_registry("bad_yaml")


def test_load_registry_validation_error(facts_service, temp_facts_dir):
    """Test error when YAML data fails Pydantic validation."""
    # Create YAML with missing required fields
    invalid_data = {
        "version": "1.0.0",
        # Missing last_updated, scope, facts
    }
    yaml_file = temp_facts_dir / "invalid.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(invalid_data, f)

    with pytest.raises(RegistryValidationError, match="validation failed"):
        facts_service.load_registry("invalid")


def test_load_registry_empty_facts_list(facts_service, temp_facts_dir):
    """Test error when registry has empty facts list."""
    # FactsRegistry requires at least one fact
    invalid_data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope",
        "facts": [],  # Empty list not allowed
    }
    yaml_file = temp_facts_dir / "empty_facts.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(invalid_data, f)

    with pytest.raises(RegistryValidationError):
        facts_service.load_registry("empty_facts")


def test_load_registry_duplicate_fact_ids(facts_service, temp_facts_dir):
    """Test error when registry has duplicate fact IDs."""
    invalid_data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope",
        "facts": [
            {
                "id": "rpp.test",
                "text": "Test fact 1",
                "source_url": "https://example.com",
                "last_verified": "2025-11-09",
                "confidence": "high",
            },
            {
                "id": "rpp.test",  # Duplicate ID
                "text": "Test fact 2",
                "source_url": "https://example.com",
                "last_verified": "2025-11-09",
                "confidence": "high",
            },
        ],
    }
    yaml_file = temp_facts_dir / "duplicate_ids.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(invalid_data, f)

    with pytest.raises(RegistryValidationError, match="Duplicate fact IDs"):
        facts_service.load_registry("duplicate_ids")


# ==================== Reload Registry Tests ====================


def test_reload_registry(facts_service, sample_registry_data, temp_facts_dir):
    """Test that reload_registry forces fresh load from disk."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Load first time
    registry1 = facts_service.load_registry("boston_rpp")
    assert registry1.version == "1.0.0"

    # Modify the YAML file
    sample_registry_data["version"] = "2.0.0"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Reload should get new version
    registry2 = facts_service.reload_registry("boston_rpp")
    assert registry2.version == "2.0.0"
    assert registry1 is not registry2


def test_reload_registry_not_cached(facts_service, sample_registry_data, temp_facts_dir):
    """Test reload_registry works even if registry not in cache."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Reload without loading first
    registry = facts_service.reload_registry("boston_rpp")
    assert isinstance(registry, FactsRegistry)


# ==================== Query Tests ====================


def test_get_fact_by_id_found(facts_service, sample_registry_data, temp_facts_dir):
    """Test retrieving a fact by its ID."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    fact = facts_service.get_fact_by_id("rpp.eligibility.vehicle_class")
    assert fact is not None
    assert fact.id == "rpp.eligibility.vehicle_class"
    assert "passenger vehicles" in fact.text


def test_get_fact_by_id_not_found(facts_service, sample_registry_data, temp_facts_dir):
    """Test get_fact_by_id returns None for non-existent ID."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    fact = facts_service.get_fact_by_id("nonexistent.fact.id")
    assert fact is None


def test_get_fact_by_id_no_registries_loaded(facts_service):
    """Test get_fact_by_id returns None when no registries loaded."""
    fact = facts_service.get_fact_by_id("rpp.eligibility.vehicle_class")
    assert fact is None


def test_get_facts_by_prefix(facts_service, sample_registry_data, temp_facts_dir):
    """Test retrieving facts by ID prefix."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    # Get all eligibility facts
    eligibility_facts = facts_service.get_facts_by_prefix("rpp.eligibility")
    assert len(eligibility_facts) == 2
    assert all(f.id.startswith("rpp.eligibility") for f in eligibility_facts)

    # Get all proof_of_residency facts
    residency_facts = facts_service.get_facts_by_prefix("rpp.proof_of_residency")
    assert len(residency_facts) == 1
    assert residency_facts[0].id == "rpp.proof_of_residency.count"

    # Get all RPP facts
    all_rpp_facts = facts_service.get_facts_by_prefix("rpp.")
    assert len(all_rpp_facts) == 3


def test_get_facts_by_prefix_no_matches(facts_service, sample_registry_data, temp_facts_dir):
    """Test get_facts_by_prefix returns empty list for no matches."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    facts = facts_service.get_facts_by_prefix("nonexistent.")
    assert facts == []


def test_get_facts_by_prefix_no_registries_loaded(facts_service):
    """Test get_facts_by_prefix returns empty list when no registries loaded."""
    facts = facts_service.get_facts_by_prefix("rpp.")
    assert facts == []


def test_get_all_facts(facts_service, sample_registry_data, temp_facts_dir):
    """Test retrieving all facts from all registries."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()
    assert len(all_facts) == 3
    assert all(isinstance(f, Fact) for f in all_facts)


def test_get_all_facts_multiple_registries(facts_service, sample_registry_data, temp_facts_dir):
    """Test get_all_facts returns facts from multiple registries."""
    # Create first registry
    yaml_file1 = temp_facts_dir / "registry1.yaml"
    with open(yaml_file1, "w") as f:
        yaml.dump(sample_registry_data, f)

    # Create second registry with different facts
    registry2_data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope_2",
        "facts": [
            {
                "id": "test.fact.1",
                "text": "Test fact 1",
                "source_url": "https://example.com",
                "last_verified": "2025-11-09",
                "confidence": "high",
            }
        ],
    }
    yaml_file2 = temp_facts_dir / "registry2.yaml"
    with open(yaml_file2, "w") as f:
        yaml.dump(registry2_data, f)

    # Load both registries
    facts_service.load_registry("registry1")
    facts_service.load_registry("registry2")

    # Get all facts
    all_facts = facts_service.get_all_facts()
    assert len(all_facts) == 4  # 3 from registry1 + 1 from registry2


def test_get_all_facts_no_registries_loaded(facts_service):
    """Test get_all_facts returns empty list when no registries loaded."""
    all_facts = facts_service.get_all_facts()
    assert all_facts == []


# ==================== Registry Info Tests ====================


def test_get_registry_info(facts_service, sample_registry_data, temp_facts_dir):
    """Test retrieving registry metadata."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")

    info = facts_service.get_registry_info("boston_rpp")
    assert info["registry_name"] == "boston_rpp"
    assert info["version"] == "1.0.0"
    assert info["scope"] == "boston_resident_parking_permit"
    assert info["last_updated"] == "2025-11-09"
    assert info["fact_count"] == 3


def test_get_registry_info_not_loaded(facts_service):
    """Test get_registry_info raises error if registry not loaded."""
    with pytest.raises(FactsServiceError, match="not loaded"):
        facts_service.get_registry_info("nonexistent")


def test_get_loaded_registries(facts_service, sample_registry_data, temp_facts_dir):
    """Test retrieving list of loaded registry names."""
    # Initially empty
    assert facts_service.get_loaded_registries() == []

    # Create and load registries
    yaml_file1 = temp_facts_dir / "registry1.yaml"
    with open(yaml_file1, "w") as f:
        yaml.dump(sample_registry_data, f)

    registry2_data = {**sample_registry_data, "scope": "test_scope_2"}
    yaml_file2 = temp_facts_dir / "registry2.yaml"
    with open(yaml_file2, "w") as f:
        yaml.dump(registry2_data, f)

    facts_service.load_registry("registry1")
    facts_service.load_registry("registry2")

    loaded = facts_service.get_loaded_registries()
    assert len(loaded) == 2
    assert "registry1" in loaded
    assert "registry2" in loaded


# ==================== Cache Management Tests ====================


def test_clear_cache(facts_service, sample_registry_data, temp_facts_dir):
    """Test clearing all cached registries."""
    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    facts_service.load_registry("boston_rpp")
    assert len(facts_service._cache) == 1

    facts_service.clear_cache()
    assert len(facts_service._cache) == 0
    assert facts_service.get_loaded_registries() == []


# ==================== Thread Safety Tests ====================


def test_thread_safety_concurrent_loads(facts_service, sample_registry_data, temp_facts_dir):
    """Test that concurrent loads use the lock properly (basic test)."""
    import threading

    yaml_file = temp_facts_dir / "boston_rpp.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_registry_data, f)

    results = []

    def load_registry():
        registry = facts_service.load_registry("boston_rpp")
        results.append(registry)

    # Create multiple threads
    threads = [threading.Thread(target=load_registry) for _ in range(5)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    # All should return the same cached object
    assert len(results) == 5
    assert all(r is results[0] for r in results)


# ==================== Factory Function Tests ====================


def test_get_facts_service_default_path():
    """Test get_facts_service factory with default path."""
    service = get_facts_service()
    assert isinstance(service, FactsService)
    assert service.facts_dir.name == "facts"
    assert service.facts_dir.parent.name == "docs"


def test_get_facts_service_custom_path(temp_facts_dir):
    """Test get_facts_service factory with custom path."""
    service = get_facts_service(temp_facts_dir)
    assert isinstance(service, FactsService)
    assert service.facts_dir == temp_facts_dir


def test_get_facts_service_string_path(temp_facts_dir):
    """Test get_facts_service factory with string path."""
    service = get_facts_service(str(temp_facts_dir))
    assert isinstance(service, FactsService)
    assert service.facts_dir == temp_facts_dir


# ==================== Edge Cases ====================


def test_fact_with_optional_fields(facts_service, temp_facts_dir):
    """Test loading facts with optional fields."""
    data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope",
        "facts": [
            {
                "id": "test.fact",
                "text": "Test fact",
                "source_url": "https://example.com",
                "source_section": "Section 1.2",  # Optional
                "last_verified": "2025-11-09",
                "confidence": "medium",
                "note": "This is a test note",  # Optional
            }
        ],
    }
    yaml_file = temp_facts_dir / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    registry = facts_service.load_registry("test")
    fact = registry.facts[0]
    assert fact.source_section == "Section 1.2"
    assert fact.note == "This is a test note"


def test_fact_without_optional_fields(facts_service, temp_facts_dir):
    """Test loading facts without optional fields."""
    data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope",
        "facts": [
            {
                "id": "test.fact",
                "text": "Test fact",
                "source_url": "https://example.com",
                # No source_section, no note
                "last_verified": "2025-11-09",
                "confidence": "low",
            }
        ],
    }
    yaml_file = temp_facts_dir / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    registry = facts_service.load_registry("test")
    fact = registry.facts[0]
    assert fact.source_section is None
    assert fact.note is None


def test_confidence_levels(facts_service, temp_facts_dir):
    """Test all confidence levels are properly handled."""
    facts_data = []
    for confidence in ["high", "medium", "low"]:
        facts_data.append(
            {
                "id": f"test.{confidence}",
                "text": f"Test fact with {confidence} confidence",
                "source_url": "https://example.com",
                "last_verified": "2025-11-09",
                "confidence": confidence,
            }
        )

    data = {
        "version": "1.0.0",
        "last_updated": "2025-11-09",
        "scope": "test_scope",
        "facts": facts_data,
    }
    yaml_file = temp_facts_dir / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    registry = facts_service.load_registry("test")
    assert len(registry.facts) == 3
    assert registry.facts[0].confidence == ConfidenceLevel.HIGH
    assert registry.facts[1].confidence == ConfidenceLevel.MEDIUM
    assert registry.facts[2].confidence == ConfidenceLevel.LOW
