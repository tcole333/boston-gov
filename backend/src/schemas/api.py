"""Pydantic schemas for API request/response models.

This module defines simplified response models for API endpoints that differ
from the full Neo4j graph schemas. These models are optimized for frontend
consumption and may omit internal fields or flatten complex relationships.
"""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DocumentTypeResponse(BaseModel):
    """Simplified document type response for frontend consumption.

    This model represents what documents are required for a process,
    optimized for display in the document upload UI.

    Attributes:
        id: Unique identifier (e.g., 'proof_of_residency')
        label: Human-readable name for display
        description: Detailed description of what's accepted
        accepted_formats: List of file extensions (e.g., ['pdf', 'jpg', 'png'])
        max_size_mb: Maximum file size in megabytes
        required: Whether this document is required (vs optional)
        source_url: Official source URL for regulatory citation
        source_section: Specific section of source document
        last_verified: Date verified in YYYY-MM-DD format
        confidence: Confidence level (high|medium|low)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "proof_of_residency",
                "label": "Proof of Boston Residency",
                "description": "Document proving you live in Boston (utility bill, lease, etc.)",
                "accepted_formats": ["pdf", "jpg", "png"],
                "max_size_mb": 10,
                "required": True,
                "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                "source_section": "Proof of Boston residency",
                "last_verified": "2025-11-09",
                "confidence": "high",
            }
        }
    )

    id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier (e.g., 'proof_of_residency')",
    )
    label: str = Field(
        ..., min_length=1, max_length=200, description="Human-readable name for display"
    )
    description: str = Field(..., min_length=1, description="Detailed description of what's accepted")
    accepted_formats: list[str] = Field(
        ..., min_length=1, description="File extensions accepted (e.g., ['pdf', 'jpg', 'png'])"
    )
    max_size_mb: int = Field(..., ge=1, le=100, description="Maximum file size in megabytes")
    required: bool = Field(..., description="Whether this document is required (vs optional)")

    # Citations (REQUIRED for regulatory data)
    source_url: HttpUrl = Field(..., description="Official source URL")
    source_section: str = Field(..., min_length=1, description="Specific section of source")
    last_verified: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date verified (YYYY-MM-DD)"
    )
    confidence: str = Field(..., pattern=r"^(high|medium|low)$", description="Confidence level")


__all__ = [
    "DocumentTypeResponse",
]
