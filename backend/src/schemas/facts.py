"""Pydantic schemas for Facts Registry.

The Facts Registry is the citation system that ensures all regulatory claims are
traceable to official sources. Facts are stored in YAML files (e.g., /docs/facts/boston_rpp.yaml)
and loaded into these schemas for validation and type safety.

All regulatory data in the system must reference facts from this registry.

Example:
    ```python
    import yaml
    from schemas.facts import FactsRegistry

    with open("docs/facts/boston_rpp.yaml") as f:
        data = yaml.safe_load(f)
        registry = FactsRegistry(**data)

    # Access facts
    for fact in registry.facts:
        print(f"{fact.id}: {fact.text}")
        print(f"  Source: {fact.source_url}")
        print(f"  Confidence: {fact.confidence}")
    ```
"""

from datetime import date

from pydantic import BaseModel, Field, HttpUrl, field_validator

from .graph import ConfidenceLevel


class Fact(BaseModel):
    """Individual regulatory fact with citation metadata.

    Every fact in the registry must be traceable to an official source and include
    verification information. Facts are the atomic units of regulatory knowledge.

    Attributes:
        id: Unique hierarchical identifier (e.g., "rpp.eligibility.vehicle_class")
        text: Human-readable regulatory claim (the actual fact)
        source_url: URL to official source document (regulation, webpage, PDF)
        source_section: Section/page reference within the source (optional)
        last_verified: Date when this fact was last verified against the source
        confidence: Confidence level in this fact's accuracy
        note: Additional context or caveats (optional)

    Examples:
        ```python
        fact = Fact(
            id="rpp.proof_of_residency.recency",
            text="Proof of residency must be dated within 30 days",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Proof of Boston residency",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH
        )
        ```
    """

    id: str = Field(
        min_length=1,
        max_length=200,
        description="Unique hierarchical identifier (e.g., 'rpp.eligibility.vehicle_class')",
    )
    text: str = Field(min_length=1, description="Human-readable regulatory claim (the actual fact)")
    source_url: HttpUrl = Field(
        description="URL to official source document (regulation, webpage, PDF)"
    )
    source_section: str | None = Field(
        default=None, description="Section/page reference within the source (optional)"
    )
    last_verified: date = Field(
        description="Date when this fact was last verified against the source (YYYY-MM-DD)"
    )
    confidence: ConfidenceLevel = Field(description="Confidence level in this fact's accuracy")
    note: str | None = Field(default=None, description="Additional context or caveats (optional)")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate that fact ID is not empty or whitespace-only.

        Fact IDs should follow a hierarchical naming convention using dots:
        - Format: scope.category.subcategory.detail
        - Example: rpp.eligibility.vehicle_class
        - Example: rpp.proof_of_residency.recency

        Args:
            v: The fact ID to validate

        Returns:
            The stripped fact ID

        Raises:
            ValueError: If the fact ID is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Fact ID cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate that fact text is not empty or whitespace-only.

        Args:
            v: The fact text to validate

        Returns:
            The stripped fact text

        Raises:
            ValueError: If the fact text is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Fact text cannot be empty or whitespace-only")
        return v.strip()


class FactsRegistry(BaseModel):
    """Root container for all facts in a Facts Registry YAML file.

    The Facts Registry maintains a versioned, auditable collection of regulatory facts.
    Each registry file typically corresponds to one government process (e.g., Boston RPP).

    Attributes:
        version: Semantic version of this registry (e.g., "1.0.0")
        last_updated: Date when this registry was last updated
        scope: Scope identifier for this registry (e.g., "boston_resident_parking_permit")
        facts: List of regulatory facts

    Examples:
        ```python
        import yaml
        from schemas.facts import FactsRegistry

        # Load from YAML
        with open("docs/facts/boston_rpp.yaml") as f:
            data = yaml.safe_load(f)
            registry = FactsRegistry(**data)

        print(f"Registry version: {registry.version}")
        print(f"Last updated: {registry.last_updated}")
        print(f"Total facts: {len(registry.facts)}")

        # Find facts by ID prefix
        eligibility_facts = [
            fact for fact in registry.facts
            if fact.id.startswith("rpp.eligibility")
        ]
        ```
    """

    version: str = Field(
        min_length=1,
        max_length=20,
        description="Semantic version of this registry (e.g., '1.0.0')",
    )
    last_updated: date = Field(description="Date when this registry was last updated (YYYY-MM-DD)")
    scope: str = Field(
        min_length=1,
        max_length=200,
        description="Scope identifier for this registry (e.g., 'boston_resident_parking_permit')",
    )
    facts: list[Fact] = Field(description="List of regulatory facts", min_length=1)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate that version is not empty or whitespace-only.

        Should follow semantic versioning (major.minor.patch) but this is not strictly enforced.

        Args:
            v: The version string to validate

        Returns:
            The stripped version string

        Raises:
            ValueError: If the version is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Version cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """Validate that scope is not empty or whitespace-only.

        Args:
            v: The scope string to validate

        Returns:
            The stripped scope string

        Raises:
            ValueError: If the scope is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Scope cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("facts")
    @classmethod
    def validate_unique_fact_ids(cls, v: list[Fact]) -> list[Fact]:
        """Validate that all fact IDs are unique within the registry.

        Args:
            v: The list of facts to validate

        Returns:
            The list of facts

        Raises:
            ValueError: If duplicate fact IDs are found
        """
        fact_ids = [fact.id for fact in v]
        duplicates = [fact_id for fact_id in fact_ids if fact_ids.count(fact_id) > 1]
        if duplicates:
            unique_duplicates = list(set(duplicates))
            raise ValueError(
                f"Duplicate fact IDs found in registry: {', '.join(unique_duplicates)}"
            )
        return v


# Export all schemas for easy importing
__all__ = [
    "Fact",
    "FactsRegistry",
]
