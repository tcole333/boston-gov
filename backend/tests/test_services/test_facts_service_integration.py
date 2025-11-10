"""Integration tests for FactsService using actual boston_rpp.yaml file.

These tests verify that the service works correctly with real YAML files
from the docs/facts/ directory.
"""

from pathlib import Path

import pytest

from src.services.facts_service import FactsService, get_facts_service


@pytest.fixture
def project_root():
    """Get the project root directory."""
    # Go up from backend/tests/test_services/ to project root
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def facts_dir(project_root):
    """Get the actual facts directory."""
    return project_root / "docs" / "facts"


@pytest.fixture
def facts_service(facts_dir):
    """Create a FactsService with the actual facts directory."""
    return FactsService(facts_dir)


@pytest.mark.integration
def test_load_actual_boston_rpp_registry(facts_service):
    """Test loading the actual boston_rpp.yaml file."""
    registry = facts_service.load_registry("boston_rpp")

    # Verify basic registry metadata
    assert registry.version == "1.0.0"
    assert registry.scope == "boston_resident_parking_permit"
    assert registry.last_updated.year == 2025
    assert registry.last_updated.month == 11
    assert registry.last_updated.day == 9

    # Verify facts were loaded
    assert len(registry.facts) > 0
    print(f"Loaded {len(registry.facts)} facts from boston_rpp.yaml")


@pytest.mark.integration
def test_actual_fact_ids_are_unique(facts_service):
    """Test that all fact IDs in boston_rpp.yaml are unique."""
    registry = facts_service.load_registry("boston_rpp")

    fact_ids = [fact.id for fact in registry.facts]
    assert len(fact_ids) == len(set(fact_ids)), "Duplicate fact IDs found"


@pytest.mark.integration
def test_actual_facts_have_required_fields(facts_service):
    """Test that all facts have required fields populated."""
    registry = facts_service.load_registry("boston_rpp")

    for fact in registry.facts:
        # Check required fields
        assert fact.id, "Fact ID is empty"
        assert fact.text, "Fact text is empty"
        assert fact.source_url, "Fact source_url is empty"
        assert fact.last_verified, "Fact last_verified is missing"
        assert fact.confidence, "Fact confidence is missing"

        # Verify ID follows naming convention (starts with rpp.)
        assert fact.id.startswith("rpp."), f"Fact ID '{fact.id}' doesn't follow naming convention"


@pytest.mark.integration
def test_query_actual_eligibility_facts(facts_service):
    """Test querying eligibility facts from actual boston_rpp.yaml."""
    facts_service.load_registry("boston_rpp")

    eligibility_facts = facts_service.get_facts_by_prefix("rpp.eligibility")

    # Should have at least the core eligibility facts
    assert len(eligibility_facts) >= 3, "Expected at least 3 eligibility facts"

    # Verify specific known facts exist
    fact_ids = [f.id for f in eligibility_facts]
    assert "rpp.eligibility.vehicle_class" in fact_ids
    assert "rpp.eligibility.registration_state" in fact_ids
    assert "rpp.eligibility.no_unpaid_tickets" in fact_ids


@pytest.mark.integration
def test_query_actual_fact_by_id(facts_service):
    """Test retrieving a specific fact from boston_rpp.yaml by ID."""
    facts_service.load_registry("boston_rpp")

    fact = facts_service.get_fact_by_id("rpp.eligibility.vehicle_class")

    assert fact is not None
    assert fact.id == "rpp.eligibility.vehicle_class"
    assert "passenger vehicles" in fact.text.lower()
    assert fact.confidence.value == "high"


@pytest.mark.integration
def test_actual_proof_of_residency_facts(facts_service):
    """Test querying proof of residency facts."""
    facts_service.load_registry("boston_rpp")

    residency_facts = facts_service.get_facts_by_prefix("rpp.proof_of_residency")

    # Should have multiple proof of residency requirements
    assert len(residency_facts) >= 5

    # Check for known facts
    fact_ids = [f.id for f in residency_facts]
    assert "rpp.proof_of_residency.count" in fact_ids
    assert "rpp.proof_of_residency.recency" in fact_ids
    assert "rpp.proof_of_residency.name_match" in fact_ids
    assert "rpp.proof_of_residency.accepted_types" in fact_ids


@pytest.mark.integration
def test_actual_permit_facts(facts_service):
    """Test querying permit facts."""
    facts_service.load_registry("boston_rpp")

    permit_facts = facts_service.get_facts_by_prefix("rpp.permit")

    # Should have permit-related facts
    assert len(permit_facts) >= 3

    # Check for known facts
    fact_ids = [f.id for f in permit_facts]
    assert "rpp.permit.cost" in fact_ids
    assert "rpp.permit.in_person_timing" in fact_ids
    assert "rpp.permit.sticker_placement" in fact_ids


@pytest.mark.integration
def test_actual_office_facts(facts_service):
    """Test querying office information facts."""
    facts_service.load_registry("boston_rpp")

    office_facts = facts_service.get_facts_by_prefix("rpp.office")

    # Should have office information
    assert len(office_facts) >= 4

    # Check for known facts
    fact_ids = [f.id for f in office_facts]
    assert "rpp.office.location" in fact_ids
    assert "rpp.office.hours" in fact_ids
    assert "rpp.office.phone" in fact_ids
    assert "rpp.office.email" in fact_ids


@pytest.mark.integration
def test_actual_enforcement_facts(facts_service):
    """Test querying enforcement facts."""
    facts_service.load_registry("boston_rpp")

    enforcement_facts = facts_service.get_facts_by_prefix("rpp.enforcement")

    # Should have enforcement information
    assert len(enforcement_facts) >= 4

    # Check for known facts
    fact_ids = [f.id for f in enforcement_facts]
    assert "rpp.enforcement.violation_fine" in fact_ids
    assert "rpp.enforcement.revocation" in fact_ids


@pytest.mark.integration
def test_actual_rental_facts(facts_service):
    """Test querying rental car permit facts."""
    facts_service.load_registry("boston_rpp")

    rental_facts = facts_service.get_facts_by_prefix("rpp.rental")

    # Should have rental car permit facts
    assert len(rental_facts) >= 3

    # Check for known facts
    fact_ids = [f.id for f in rental_facts]
    assert "rpp.rental.max_duration" in fact_ids


@pytest.mark.integration
def test_get_all_facts_from_boston_rpp(facts_service):
    """Test retrieving all facts from boston_rpp.yaml."""
    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()

    # Should have a substantial number of facts
    assert len(all_facts) >= 25, f"Expected at least 25 facts, got {len(all_facts)}"

    # All should be from RPP scope
    assert all(f.id.startswith("rpp.") for f in all_facts)


@pytest.mark.integration
def test_registry_info_boston_rpp(facts_service):
    """Test getting registry info for boston_rpp."""
    facts_service.load_registry("boston_rpp")

    info = facts_service.get_registry_info("boston_rpp")

    assert info["registry_name"] == "boston_rpp"
    assert info["version"] == "1.0.0"
    assert info["scope"] == "boston_resident_parking_permit"
    assert info["last_updated"] == "2025-11-09"
    assert info["fact_count"] >= 25


@pytest.mark.integration
def test_caching_with_actual_file(facts_service):
    """Test that actual file is cached on first load."""
    # Load first time
    registry1 = facts_service.load_registry("boston_rpp")

    # Load second time (should be from cache)
    registry2 = facts_service.load_registry("boston_rpp")

    # Should be the same object
    assert registry1 is registry2


@pytest.mark.integration
def test_reload_with_actual_file(facts_service):
    """Test reloading actual file bypasses cache."""
    # Load first time
    registry1 = facts_service.load_registry("boston_rpp")

    # Reload (should be new object)
    registry2 = facts_service.reload_registry("boston_rpp")

    # Should be different objects but same data
    assert registry1 is not registry2
    assert registry1.version == registry2.version
    assert len(registry1.facts) == len(registry2.facts)


@pytest.mark.integration
def test_factory_function_with_default_path():
    """Test get_facts_service factory function loads actual file."""
    service = get_facts_service()

    # Should be able to load boston_rpp
    registry = service.load_registry("boston_rpp")
    assert registry.scope == "boston_resident_parking_permit"


@pytest.mark.integration
def test_all_facts_have_valid_urls(facts_service):
    """Test that all facts have valid source URLs."""
    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()

    for fact in all_facts:
        # URL should be a string and start with https://
        assert str(fact.source_url).startswith("https://") or str(fact.source_url).startswith(
            "http://"
        )
        # URL should contain boston.gov
        assert "boston.gov" in str(fact.source_url).lower()


@pytest.mark.integration
def test_facts_last_verified_dates_are_recent(facts_service):
    """Test that facts have recent verification dates."""
    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()

    for fact in all_facts:
        # All facts should be verified in 2025 (current context)
        assert fact.last_verified.year == 2025
        # Should be verified in November 2025
        assert fact.last_verified.month == 11


@pytest.mark.integration
def test_confidence_levels_distribution(facts_service):
    """Test that facts have appropriate confidence levels."""
    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()

    # Count confidence levels
    high_count = sum(1 for f in all_facts if f.confidence.value == "high")
    medium_count = sum(1 for f in all_facts if f.confidence.value == "medium")
    low_count = sum(1 for f in all_facts if f.confidence.value == "low")

    # Most facts should be high confidence (official sources)
    assert high_count > 0, "Expected at least some high confidence facts"

    print(f"Confidence distribution: High={high_count}, Medium={medium_count}, Low={low_count}")


@pytest.mark.integration
def test_hierarchical_fact_ids(facts_service):
    """Test that fact IDs follow hierarchical structure."""
    facts_service.load_registry("boston_rpp")

    all_facts = facts_service.get_all_facts()

    # Check ID structure
    for fact in all_facts:
        parts = fact.id.split(".")
        # Should have at least 2 parts (e.g., rpp.eligibility)
        assert len(parts) >= 2, f"Fact ID '{fact.id}' doesn't follow hierarchy"
        # First part should be "rpp"
        assert parts[0] == "rpp", f"Fact ID '{fact.id}' doesn't start with 'rpp'"


@pytest.mark.integration
def test_multiple_category_prefixes(facts_service):
    """Test that facts exist in multiple categories."""
    facts_service.load_registry("boston_rpp")

    # Check various categories have facts
    categories_to_check = [
        "rpp.eligibility",
        "rpp.proof_of_residency",
        "rpp.permit",
        "rpp.office",
        "rpp.enforcement",
        "rpp.rental",
    ]

    for category in categories_to_check:
        facts = facts_service.get_facts_by_prefix(category)
        assert len(facts) > 0, f"No facts found for category '{category}'"


@pytest.mark.integration
def test_clear_cache_with_actual_file(facts_service):
    """Test clearing cache works with actual file."""
    # Load registry
    facts_service.load_registry("boston_rpp")
    assert len(facts_service.get_loaded_registries()) == 1

    # Clear cache
    facts_service.clear_cache()
    assert len(facts_service.get_loaded_registries()) == 0

    # Should be able to reload
    registry = facts_service.load_registry("boston_rpp")
    assert registry.scope == "boston_resident_parking_permit"
