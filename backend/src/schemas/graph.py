"""Pydantic schemas for Neo4j graph entities.

This module defines schemas for all node types in the government processes graph,
as specified in /docs/data_model.md.

All regulatory entities (Process, Step, Requirement, Rule, DocumentType, Office, etc.)
include citation fields for source traceability.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ConfidenceLevel(str, Enum):
    """Confidence score for regulatory claims.

    Attributes:
        HIGH: Direct quote from official source
        MEDIUM: Inferred from official source
        LOW: Ambiguous or uncertain
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProcessCategory(str, Enum):
    """Categories of government processes.

    Attributes:
        PERMITS: Parking permits, building permits, etc.
        LICENSES: Professional licenses, business licenses, etc.
        BENEFITS: Government benefits programs
    """

    PERMITS = "permits"
    LICENSES = "licenses"
    BENEFITS = "benefits"


class WebResourceType(str, Enum):
    """Types of web resources.

    Attributes:
        HOW_TO: How-to guide or instructions
        PROGRAM: Program overview page
        PORTAL: Online application portal
        PDF_FORM: PDF form download
    """

    HOW_TO = "how_to"
    PROGRAM = "program"
    PORTAL = "portal"
    PDF_FORM = "pdf_form"


class ApplicationStatus(str, Enum):
    """Status of a user application.

    Attributes:
        PENDING: Application submitted, awaiting review
        APPROVED: Application approved
        DENIED: Application denied
    """

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class ApplicationCategory(str, Enum):
    """Category of application.

    Attributes:
        NEW: New application
        RENEWAL: Renewal of existing permit/license
        REPLACEMENT: Replacement of lost/stolen permit
        RENTAL: Rental-specific application
    """

    NEW = "new"
    RENEWAL = "renewal"
    REPLACEMENT = "replacement"
    RENTAL = "rental"


class TimestampMixin(BaseModel):
    """Base mixin for timestamp fields.

    Attributes:
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when record was last updated"
    )


class CitationMixin(BaseModel):
    """Base mixin for citation/provenance fields.

    All regulatory data must be traceable to official sources.

    Attributes:
        source_url: URL to official source document
        last_verified: Date when information was last verified
        confidence: Confidence level in this data
    """

    source_url: HttpUrl = Field(description="URL to official source (regulation, webpage, PDF)")
    last_verified: date = Field(
        description="Date when this information was last verified (YYYY-MM-DD)"
    )
    confidence: ConfidenceLevel = Field(description="Confidence level in this data")


class Process(CitationMixin, TimestampMixin):
    """High-level government service or process.

    Example: "Boston Resident Parking Permit"

    Attributes:
        process_id: Unique identifier (e.g., "boston_rpp")
        name: Display name
        description: One-sentence summary
        category: Process category (permits, licenses, benefits)
        jurisdiction: Governing authority (e.g., "City of Boston")
    """

    process_id: str = Field(min_length=1, max_length=100, description="Unique process identifier")
    name: str = Field(min_length=1, max_length=200, description="Human-readable process name")
    description: str = Field(min_length=1, description="One-sentence summary of the process")
    category: ProcessCategory = Field(description="Process category")
    jurisdiction: str = Field(
        min_length=1, max_length=200, description="Governing authority (e.g., 'City of Boston')"
    )


class Step(CitationMixin, TimestampMixin):
    """Actionable task within a process.

    Example: "Gather proof of residency"

    Attributes:
        step_id: Unique identifier (e.g., "rpp.gather_proof")
        process_id: Parent process identifier
        name: Short label for the step
        description: Full action description
        order: Sequence number for display
        estimated_time_minutes: Official time estimate
        observed_time_minutes: Median from user feedback (optional)
        cost_usd: Cost in USD if applicable
        optional: Whether step can be skipped
    """

    step_id: str = Field(min_length=1, max_length=100, description="Unique step identifier")
    process_id: str = Field(min_length=1, max_length=100, description="Parent process ID")
    name: str = Field(min_length=1, max_length=200, description="Short step label")
    description: str = Field(min_length=1, description="Full action description")
    order: int = Field(ge=1, description="Sequence number (1-indexed)")
    estimated_time_minutes: int | None = Field(
        default=None, ge=0, description="Official time estimate in minutes"
    )
    observed_time_minutes: int | None = Field(
        default=None, ge=0, description="Median time from user feedback"
    )
    cost_usd: float = Field(default=0.0, ge=0.0, description="Cost in USD")
    optional: bool = Field(default=False, description="Whether this step can be skipped")


class Requirement(CitationMixin, TimestampMixin):
    """Eligibility condition or rule.

    Example: "MA registration at Boston address"

    Attributes:
        requirement_id: Unique identifier (e.g., "rpp.req.ma_registration")
        text: Human-readable description
        fact_id: Reference to Facts Registry
        applies_to_process: Process ID this applies to
        hard_gate: Whether this blocks progress if not met
        source_section: Page/PDF section (optional)
    """

    requirement_id: str = Field(
        min_length=1, max_length=100, description="Unique requirement identifier"
    )
    text: str = Field(min_length=1, description="Human-readable requirement description")
    fact_id: str = Field(
        min_length=1,
        max_length=100,
        description="Reference to Facts Registry (e.g., 'rpp.eligibility.registration_state')",
    )
    applies_to_process: str = Field(
        min_length=1, max_length=100, description="Process ID this requirement applies to"
    )
    hard_gate: bool = Field(default=True, description="Whether this blocks progress if not met")
    source_section: str | None = Field(default=None, description="Page or PDF section reference")


class Rule(CitationMixin, TimestampMixin):
    """Atomic regulatory fact.

    Example: "Proof of residency ≤30 days"

    Attributes:
        rule_id: Unique identifier (e.g., "RPP-15-4A")
        text: Exact regulation text
        fact_id: Reference to Facts Registry
        scope: Scope of rule (general, rental, military, etc.)
        source_section: Section/page number
        effective_date: When rule took effect (optional)
    """

    rule_id: str = Field(min_length=1, max_length=100, description="Unique rule identifier")
    text: str = Field(min_length=1, description="Exact regulation text")
    fact_id: str = Field(min_length=1, max_length=100, description="Reference to Facts Registry")
    scope: str = Field(
        default="general",
        min_length=1,
        max_length=100,
        description="Scope of rule (e.g., 'general', 'rental', 'military')",
    )
    source_section: str = Field(min_length=1, description="Section/page number reference")
    effective_date: date | None = Field(default=None, description="When this rule took effect")


class DocumentType(CitationMixin, TimestampMixin):
    """Template for accepted documents.

    Example: "Utility bill ≤30 days"

    Attributes:
        doc_type_id: Unique identifier (e.g., "proof.utility_bill")
        name: Display name
        freshness_days: Maximum age in days
        name_match_required: Must match applicant name
        address_match_required: Must match Boston address
        examples: List of example issuers
    """

    doc_type_id: str = Field(
        min_length=1, max_length=100, description="Unique document type identifier"
    )
    name: str = Field(min_length=1, max_length=200, description="Human-readable document type name")
    freshness_days: int = Field(ge=0, description="Maximum age in days (e.g., 30)")
    name_match_required: bool = Field(
        default=True, description="Whether document name must match applicant name"
    )
    address_match_required: bool = Field(
        default=True, description="Whether document address must match Boston address"
    )
    examples: list[str] = Field(
        default_factory=list,
        description="List of example issuers (e.g., ['National Grid', 'Eversource'])",
    )


class Document(TimestampMixin):
    """User-provided document instance.

    Note: No citation fields - this is user data, not regulatory data.
    Documents are auto-deleted after 24 hours.

    Attributes:
        doc_id: Unique identifier (UUID)
        doc_type_id: Reference to DocumentType
        issuer: Document issuer (e.g., "National Grid")
        issue_date: Date from OCR
        name_on_doc: Name from OCR
        address_on_doc: Address from OCR
        file_ref: S3/local path (deleted after 24h)
        verified: Whether document passed validation
        validation_errors: List of validation errors if any
        deleted_at: Auto-set to created_at + 24h
    """

    doc_id: str = Field(min_length=1, description="Unique document ID (UUID)")
    doc_type_id: str = Field(min_length=1, max_length=100, description="Reference to DocumentType")
    issuer: str = Field(min_length=1, max_length=200, description="Document issuer (from OCR)")
    issue_date: date = Field(description="Issue date (from OCR)")
    name_on_doc: str = Field(
        min_length=1, max_length=200, description="Name on document (from OCR)"
    )
    address_on_doc: str = Field(min_length=1, description="Address on document (from OCR)")
    file_ref: str = Field(min_length=1, description="File path (S3/local, deleted after 24h)")
    verified: bool = Field(default=False, description="Whether document passed validation")
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors if any"
    )
    deleted_at: datetime | None = Field(
        default=None, description="When document will be/was deleted (created_at + 24h)"
    )


class Office(CitationMixin, TimestampMixin):
    """Physical location for in-person steps.

    Example: "Office of the Parking Clerk"

    Attributes:
        office_id: Unique identifier (e.g., "parking_clerk")
        name: Office name
        address: Full street address
        room: Room number (optional)
        hours: Operating hours
        phone: Phone number (optional)
        email: Email address (optional)
    """

    office_id: str = Field(min_length=1, max_length=100, description="Unique office identifier")
    name: str = Field(min_length=1, max_length=200, description="Office name")
    address: str = Field(min_length=1, description="Full street address")
    room: str | None = Field(default=None, description="Room number")
    hours: str = Field(min_length=1, description="Operating hours (e.g., 'Mon-Fri, 9:00-4:30')")
    phone: str | None = Field(default=None, description="Phone number")
    email: str | None = Field(default=None, description="Email address")


class RPPNeighborhood(CitationMixin, TimestampMixin):
    """Boston parking neighborhood (RPP-specific).

    Attributes:
        nbrhd_id: Unique identifier (e.g., "back_bay")
        name: Display name
        auto_renew_cycle: Next audit date (optional)
        posted_streets: List of streets with RPP signage
        notes: Special rules (optional)
    """

    nbrhd_id: str = Field(
        min_length=1, max_length=100, description="Unique neighborhood identifier"
    )
    name: str = Field(min_length=1, max_length=200, description="Neighborhood display name")
    auto_renew_cycle: date | None = Field(default=None, description="Next auto-renewal audit date")
    posted_streets: list[str] = Field(
        default_factory=list, description="Street names with RPP signage"
    )
    notes: str | None = Field(default=None, description="Special rules or notes")


class WebResource(TimestampMixin):
    """Official web resource (page, PDF, portal).

    Note: No citation fields - this IS a source, not derived from one.

    Attributes:
        res_id: Unique identifier (e.g., "howto")
        title: Page title
        url: Full URL (must be unique)
        type: Resource type
        owner: Owning office/department
        last_seen: Last successful fetch date
        hash: SHA256 of content for change detection
    """

    res_id: str = Field(min_length=1, max_length=100, description="Unique resource identifier")
    title: str = Field(min_length=1, max_length=500, description="Page title")
    url: HttpUrl = Field(description="Full URL (must be unique)")
    type: WebResourceType = Field(description="Resource type")
    owner: str = Field(
        min_length=1,
        max_length=200,
        description="Owning office/department (e.g., 'Parking Clerk', 'BTD')",
    )
    last_seen: date = Field(description="Last successful fetch date")
    hash: str = Field(
        min_length=64, max_length=64, description="SHA256 hash of content for change detection"
    )

    @field_validator("hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate that hash is a valid SHA256 hex string."""
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Hash must be a valid SHA256 hex string")
        return v.lower()


class Person(BaseModel):
    """User (optional, for tracking).

    Note: Minimal PII - only for Phase 2+.

    Attributes:
        person_id: Unique identifier (UUID)
        email: Hashed email address
        created_at: When user record was created
    """

    person_id: str = Field(min_length=1, description="Unique person ID (UUID)")
    email: str = Field(min_length=1, description="Hashed email address")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When user record was created"
    )


class Application(TimestampMixin):
    """User's process session (Phase 2+).

    Attributes:
        app_id: Unique identifier (UUID)
        process_id: Process being applied for
        category: Application category
        submitted_on: When application was submitted (optional)
        status: Current status
        reason_if_denied: Denial reason (optional)
    """

    app_id: str = Field(min_length=1, description="Unique application ID (UUID)")
    process_id: str = Field(
        min_length=1, max_length=100, description="Process ID (e.g., 'boston_rpp')"
    )
    category: ApplicationCategory = Field(description="Application category")
    submitted_on: datetime | None = Field(
        default=None, description="When application was submitted"
    )
    status: ApplicationStatus = Field(
        default=ApplicationStatus.PENDING, description="Current application status"
    )
    reason_if_denied: str | None = Field(
        default=None, description="Reason for denial if status is DENIED"
    )


# Export all schemas for easy importing
__all__ = [
    "ConfidenceLevel",
    "ProcessCategory",
    "WebResourceType",
    "ApplicationStatus",
    "ApplicationCategory",
    "TimestampMixin",
    "CitationMixin",
    "Process",
    "Step",
    "Requirement",
    "Rule",
    "DocumentType",
    "Document",
    "Office",
    "RPPNeighborhood",
    "WebResource",
    "Person",
    "Application",
]
