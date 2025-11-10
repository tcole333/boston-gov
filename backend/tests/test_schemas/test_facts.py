"""Unit tests for Facts Registry schemas.

Tests cover:
- Valid schema instantiation
- Field validation (types, constraints, URLs, dates)
- Invalid data rejection
- Edge cases
- Serialization/deserialization
- Loading actual YAML data
- Duplicate fact ID detection
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from src.schemas.facts import Fact, FactsRegistry
from src.schemas.graph import ConfidenceLevel


# Fixtures for common test data
@pytest.fixture
def valid_fact_data() -> dict[str, Any]:
    """Provide valid fact data for testing."""
    return {
        "id": "rpp.eligibility.vehicle_class",
        "text": "Eligible vehicles are passenger vehicles or commercial vehicles under 1 ton",
        "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "source_section": "Vehicle eligibility",
        "last_verified": date(2025, 11, 9),
        "confidence": ConfidenceLevel.HIGH,
    }


@pytest.fixture
def valid_fact_minimal() -> dict[str, Any]:
    """Provide minimal valid fact data (no optional fields)."""
    return {
        "id": "rpp.test.minimal",
        "text": "A minimal test fact",
        "source_url": "https://www.boston.gov/test",
        "last_verified": date(2025, 11, 9),
        "confidence": ConfidenceLevel.MEDIUM,
    }


@pytest.fixture
def valid_registry_data(valid_fact_data: dict[str, Any]) -> dict[str, Any]:
    """Provide valid registry data for testing."""
    return {
        "version": "1.0.0",
        "last_updated": date(2025, 11, 9),
        "scope": "boston_resident_parking_permit",
        "facts": [valid_fact_data],
    }


@pytest.fixture
def boston_rpp_yaml_path() -> Path:
    """Provide path to the actual boston_rpp.yaml file."""
    # Navigate from backend/tests/test_schemas to project root
    return Path(__file__).parent.parent.parent.parent / "docs" / "facts" / "boston_rpp.yaml"


class TestFact:
    """Test Fact schema."""

    def test_valid_fact_full(self, valid_fact_data: dict[str, Any]) -> None:
        """Test creating a fact with all fields."""
        fact = Fact(**valid_fact_data)
        assert fact.id == "rpp.eligibility.vehicle_class"
        assert (
            fact.text
            == "Eligible vehicles are passenger vehicles or commercial vehicles under 1 ton"
        )
        assert (
            str(fact.source_url)
            == "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"
        )
        assert fact.source_section == "Vehicle eligibility"
        assert fact.last_verified == date(2025, 11, 9)
        assert fact.confidence == ConfidenceLevel.HIGH
        assert fact.note is None

    def test_valid_fact_minimal(self, valid_fact_minimal: dict[str, Any]) -> None:
        """Test creating a fact with only required fields."""
        fact = Fact(**valid_fact_minimal)
        assert fact.id == "rpp.test.minimal"
        assert fact.text == "A minimal test fact"
        assert fact.source_section is None
        assert fact.note is None

    def test_fact_with_note(self, valid_fact_data: dict[str, Any]) -> None:
        """Test creating a fact with an optional note."""
        data = valid_fact_data.copy()
        data["note"] = "Timing is typical/observed, not guaranteed"
        fact = Fact(**data)
        assert fact.note == "Timing is typical/observed, not guaranteed"

    def test_fact_hierarchical_id(self) -> None:
        """Test facts with hierarchical IDs."""
        test_ids = [
            "rpp.eligibility.vehicle_class",
            "rpp.proof_of_residency.count",
            "rpp.proof_of_residency.lease_move_in_recency",
            "rpp.office.location",
            "rpp.enforcement.violation_fine",
        ]
        for fact_id in test_ids:
            fact = Fact(
                id=fact_id,
                text="Test fact",
                source_url="https://www.boston.gov/test",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
            assert fact.id == fact_id

    def test_fact_confidence_levels(self, valid_fact_data: dict[str, Any]) -> None:
        """Test all confidence levels."""
        for confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]:
            data = valid_fact_data.copy()
            data["confidence"] = confidence
            fact = Fact(**data)
            assert fact.confidence == confidence

    def test_fact_id_empty_string(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that empty fact ID raises ValidationError."""
        data = valid_fact_data.copy()
        data["id"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        # Pydantic min_length constraint triggers before custom validator
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_fact_id_whitespace_only(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that whitespace-only fact ID raises ValidationError."""
        data = valid_fact_data.copy()
        data["id"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        assert "Fact ID cannot be empty" in str(exc_info.value)

    def test_fact_text_empty_string(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that empty fact text raises ValidationError."""
        data = valid_fact_data.copy()
        data["text"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        # Pydantic min_length constraint triggers before custom validator
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_fact_text_whitespace_only(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that whitespace-only fact text raises ValidationError."""
        data = valid_fact_data.copy()
        data["text"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        assert "Fact text cannot be empty" in str(exc_info.value)

    def test_fact_id_trimmed(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that fact ID is trimmed of whitespace."""
        data = valid_fact_data.copy()
        data["id"] = "  rpp.test.trim  "
        fact = Fact(**data)
        assert fact.id == "rpp.test.trim"

    def test_fact_text_trimmed(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that fact text is trimmed of whitespace."""
        data = valid_fact_data.copy()
        data["text"] = "  Test fact with whitespace  "
        fact = Fact(**data)
        assert fact.text == "Test fact with whitespace"

    def test_fact_invalid_url(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that invalid URL raises ValidationError."""
        data = valid_fact_data.copy()
        data["source_url"] = "not-a-url"
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        assert "source_url" in str(exc_info.value).lower()

    def test_fact_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Fact(id="test")
        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "text" in error_fields
        assert "source_url" in error_fields
        assert "last_verified" in error_fields
        assert "confidence" in error_fields

    def test_fact_invalid_date_format(self, valid_fact_data: dict[str, Any]) -> None:
        """Test that invalid date format raises ValidationError."""
        data = valid_fact_data.copy()
        data["last_verified"] = "not-a-date"
        with pytest.raises(ValidationError) as exc_info:
            Fact(**data)
        assert "last_verified" in str(exc_info.value).lower()

    def test_fact_serialization(self, valid_fact_data: dict[str, Any]) -> None:
        """Test fact serialization to dict."""
        fact = Fact(**valid_fact_data)
        data = fact.model_dump()
        assert data["id"] == "rpp.eligibility.vehicle_class"
        assert "text" in data
        assert "source_url" in data
        assert "last_verified" in data
        assert "confidence" in data

    def test_fact_json_serialization(self, valid_fact_data: dict[str, Any]) -> None:
        """Test fact JSON serialization."""
        fact = Fact(**valid_fact_data)
        json_str = fact.model_dump_json()
        assert "rpp.eligibility.vehicle_class" in json_str
        assert "https://www.boston.gov" in json_str


class TestFactsRegistry:
    """Test FactsRegistry schema."""

    def test_valid_registry(self, valid_registry_data: dict[str, Any]) -> None:
        """Test creating a valid registry."""
        registry = FactsRegistry(**valid_registry_data)
        assert registry.version == "1.0.0"
        assert registry.last_updated == date(2025, 11, 9)
        assert registry.scope == "boston_resident_parking_permit"
        assert len(registry.facts) == 1
        assert registry.facts[0].id == "rpp.eligibility.vehicle_class"

    def test_registry_multiple_facts(
        self, valid_fact_data: dict[str, Any], valid_fact_minimal: dict[str, Any]
    ) -> None:
        """Test registry with multiple facts."""
        data = {
            "version": "1.0.0",
            "last_updated": date(2025, 11, 9),
            "scope": "test_scope",
            "facts": [valid_fact_data, valid_fact_minimal],
        }
        registry = FactsRegistry(**data)
        assert len(registry.facts) == 2
        assert registry.facts[0].id == "rpp.eligibility.vehicle_class"
        assert registry.facts[1].id == "rpp.test.minimal"

    def test_registry_version_formats(self, valid_registry_data: dict[str, Any]) -> None:
        """Test various version formats."""
        version_formats = ["1.0.0", "2.1.3", "0.0.1", "10.20.30"]
        for version in version_formats:
            data = valid_registry_data.copy()
            data["version"] = version
            registry = FactsRegistry(**data)
            assert registry.version == version

    def test_registry_empty_version(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that empty version raises ValidationError."""
        data = valid_registry_data.copy()
        data["version"] = ""
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        # Pydantic min_length constraint triggers before custom validator
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_registry_whitespace_version(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that whitespace-only version raises ValidationError."""
        data = valid_registry_data.copy()
        data["version"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        assert "Version cannot be empty" in str(exc_info.value)

    def test_registry_empty_scope(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that empty scope raises ValidationError."""
        data = valid_registry_data.copy()
        data["scope"] = ""
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        # Pydantic min_length constraint triggers before custom validator
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_registry_whitespace_scope(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that whitespace-only scope raises ValidationError."""
        data = valid_registry_data.copy()
        data["scope"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        assert "Scope cannot be empty" in str(exc_info.value)

    def test_registry_version_trimmed(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that version is trimmed of whitespace."""
        data = valid_registry_data.copy()
        data["version"] = "  1.0.0  "
        registry = FactsRegistry(**data)
        assert registry.version == "1.0.0"

    def test_registry_scope_trimmed(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that scope is trimmed of whitespace."""
        data = valid_registry_data.copy()
        data["scope"] = "  test_scope  "
        registry = FactsRegistry(**data)
        assert registry.scope == "test_scope"

    def test_registry_empty_facts_list(self, valid_registry_data: dict[str, Any]) -> None:
        """Test that empty facts list raises ValidationError."""
        data = valid_registry_data.copy()
        data["facts"] = []
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        # Pydantic should enforce min_length=1
        assert "facts" in str(exc_info.value).lower()

    def test_registry_duplicate_fact_ids(
        self, valid_fact_data: dict[str, Any], valid_registry_data: dict[str, Any]
    ) -> None:
        """Test that duplicate fact IDs raise ValidationError."""
        fact1 = valid_fact_data.copy()
        fact2 = valid_fact_data.copy()
        fact2["text"] = "Different text but same ID"
        data = valid_registry_data.copy()
        data["facts"] = [fact1, fact2]
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        assert "Duplicate fact IDs found" in str(exc_info.value)
        assert "rpp.eligibility.vehicle_class" in str(exc_info.value)

    def test_registry_multiple_duplicates(self, valid_fact_data: dict[str, Any]) -> None:
        """Test detection of multiple duplicate fact IDs."""
        fact1 = valid_fact_data.copy()
        fact1["id"] = "rpp.test.dup1"
        fact2 = valid_fact_data.copy()
        fact2["id"] = "rpp.test.dup1"
        fact3 = valid_fact_data.copy()
        fact3["id"] = "rpp.test.dup2"
        fact4 = valid_fact_data.copy()
        fact4["id"] = "rpp.test.dup2"

        data = {
            "version": "1.0.0",
            "last_updated": date(2025, 11, 9),
            "scope": "test_scope",
            "facts": [fact1, fact2, fact3, fact4],
        }

        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(**data)
        error_msg = str(exc_info.value)
        assert "Duplicate fact IDs found" in error_msg
        assert "rpp.test.dup1" in error_msg
        assert "rpp.test.dup2" in error_msg

    def test_registry_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FactsRegistry(version="1.0.0")
        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "last_updated" in error_fields
        assert "scope" in error_fields
        assert "facts" in error_fields

    def test_registry_serialization(self, valid_registry_data: dict[str, Any]) -> None:
        """Test registry serialization to dict."""
        registry = FactsRegistry(**valid_registry_data)
        data = registry.model_dump()
        assert data["version"] == "1.0.0"
        assert data["scope"] == "boston_resident_parking_permit"
        assert len(data["facts"]) == 1


class TestBostonRPPYAMLIntegration:
    """Integration tests with the actual boston_rpp.yaml file."""

    def test_load_boston_rpp_yaml(self, boston_rpp_yaml_path: Path) -> None:
        """Test loading the actual boston_rpp.yaml file."""
        # Check file exists
        assert boston_rpp_yaml_path.exists(), f"File not found: {boston_rpp_yaml_path}"

        # Load YAML
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        # Validate with Pydantic
        registry = FactsRegistry(**yaml_data)

        # Basic assertions
        assert registry.version is not None
        assert registry.scope == "boston_resident_parking_permit"
        assert len(registry.facts) > 0

    def test_boston_rpp_all_facts_valid(self, boston_rpp_yaml_path: Path) -> None:
        """Test that all facts in boston_rpp.yaml are valid."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        # Check each fact has required fields
        for fact in registry.facts:
            assert fact.id
            assert fact.text
            assert fact.source_url
            assert fact.last_verified
            assert fact.confidence in [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
                ConfidenceLevel.LOW,
            ]

    def test_boston_rpp_fact_id_uniqueness(self, boston_rpp_yaml_path: Path) -> None:
        """Test that all fact IDs in boston_rpp.yaml are unique."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        fact_ids = [fact.id for fact in registry.facts]
        assert len(fact_ids) == len(set(fact_ids)), "Duplicate fact IDs found"

    def test_boston_rpp_fact_structure(self, boston_rpp_yaml_path: Path) -> None:
        """Test that boston_rpp.yaml facts follow expected structure."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        # Check for expected fact ID prefixes
        fact_ids = [fact.id for fact in registry.facts]
        prefixes = {fact_id.split(".")[0] for fact_id in fact_ids}
        assert "rpp" in prefixes, "Expected 'rpp' prefix in fact IDs"

    def test_boston_rpp_url_validity(self, boston_rpp_yaml_path: Path) -> None:
        """Test that all source URLs in boston_rpp.yaml are valid."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        # All URLs should start with https://
        for fact in registry.facts:
            assert str(fact.source_url).startswith("https://"), (
                f"Invalid URL for fact {fact.id}: {fact.source_url}"
            )

    def test_boston_rpp_date_validity(self, boston_rpp_yaml_path: Path) -> None:
        """Test that all dates in boston_rpp.yaml are valid."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        # All dates should be valid date objects after parsing
        for fact in registry.facts:
            assert isinstance(fact.last_verified, date)

        # Registry last_updated should also be valid
        assert isinstance(registry.last_updated, date)

    def test_boston_rpp_confidence_distribution(self, boston_rpp_yaml_path: Path) -> None:
        """Test confidence level distribution in boston_rpp.yaml."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        registry = FactsRegistry(**yaml_data)

        # Count confidence levels
        confidence_counts = {
            ConfidenceLevel.HIGH: 0,
            ConfidenceLevel.MEDIUM: 0,
            ConfidenceLevel.LOW: 0,
        }

        for fact in registry.facts:
            confidence_counts[fact.confidence] += 1

        # Should have at least some high-confidence facts
        assert confidence_counts[ConfidenceLevel.HIGH] > 0, (
            "Expected at least one high-confidence fact"
        )

    def test_boston_rpp_serialization_roundtrip(self, boston_rpp_yaml_path: Path) -> None:
        """Test that boston_rpp.yaml can be loaded, serialized, and reloaded."""
        with open(boston_rpp_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

        # Load into schema
        registry1 = FactsRegistry(**yaml_data)

        # Serialize to dict
        data = registry1.model_dump()

        # Reload from dict
        registry2 = FactsRegistry(**data)

        # Should be equivalent
        assert registry1.version == registry2.version
        assert registry1.scope == registry2.scope
        assert len(registry1.facts) == len(registry2.facts)
