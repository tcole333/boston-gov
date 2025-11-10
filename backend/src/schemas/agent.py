"""Pydantic schemas for agent responses.

This module defines response schemas for LLM agents, including conversation agents.
These schemas ensure consistent response formats and proper citation metadata.

Example:
    ```python
    from schemas.agent import ConversationResponse, Citation

    response = ConversationResponse(
        answer="You need [one proof of residency](https://www.boston.gov/... \"rpp.proof_of_residency.count\")",
        citations=[
            Citation(
                fact_id="rpp.proof_of_residency.count",
                url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                text="Exactly one proof of residency required"
            )
        ],
        tool_calls_made=["query_facts"]
    )
    ```
"""

from pydantic import BaseModel, Field, HttpUrl


class Citation(BaseModel):
    """A citation for a regulatory claim made in an agent response.

    Citations ensure all regulatory claims are traceable to official sources.
    They can reference either Facts Registry entries (with fact_id) or graph nodes.

    Attributes:
        fact_id: Unique fact identifier from Facts Registry (e.g., "rpp.eligibility.vehicle_class")
                 Optional for graph-based citations
        url: URL to the official source document
        text: The cited text or claim being referenced
        source_section: Optional section/page reference within the source

    Examples:
        ```python
        # Citation with fact ID (from Facts Registry)
        citation = Citation(
            fact_id="rpp.proof_of_residency.count",
            url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            text="Exactly one proof of residency required"
        )

        # Citation without fact ID (from graph data)
        citation = Citation(
            fact_id=None,
            url="https://www.boston.gov/departments/parking-clerk",
            text="Office hours are Monday-Friday, 9:00 AM - 4:30 PM"
        )
        ```
    """

    fact_id: str | None = Field(
        default=None,
        description="Unique fact identifier from Facts Registry (optional for graph citations)",
    )
    url: HttpUrl = Field(description="URL to the official source document")
    text: str = Field(min_length=1, description="The cited text or claim being referenced")
    source_section: str | None = Field(
        default=None, description="Section/page reference within the source (optional)"
    )


class ConversationResponse(BaseModel):
    """Response from a conversation agent.

    This schema ensures that conversation agents return properly formatted responses
    with inline citations and structured citation metadata.

    Attributes:
        answer: The natural language response with inline citation links
                Format: "[text](url \"fact_id\")" for cited claims
        citations: List of Citation objects for all sources referenced
        tool_calls_made: List of tool names called during response generation
                        (useful for debugging and testing)

    Examples:
        ```python
        response = ConversationResponse(
            answer=\"\"\"To get a resident parking permit, you need:

            1. [Valid Massachusetts registration](https://www.boston.gov/... \"rpp.eligibility.registration_state\")
            2. [One proof of residency within 30 days](https://www.boston.gov/... \"rpp.proof_of_residency.recency\")
            3. [No unpaid parking tickets](https://www.boston.gov/... \"rpp.eligibility.no_unpaid_tickets\")
            \"\"\",
            citations=[
                Citation(
                    fact_id="rpp.eligibility.registration_state",
                    url="https://www.boston.gov/...",
                    text="Vehicle must have valid Massachusetts registration"
                ),
                Citation(
                    fact_id="rpp.proof_of_residency.recency",
                    url="https://www.boston.gov/...",
                    text="Proof of residency must be dated within 30 days"
                ),
                Citation(
                    fact_id="rpp.eligibility.no_unpaid_tickets",
                    url="https://www.boston.gov/...",
                    text="No unpaid Boston parking tickets on the registration"
                )
            ],
            tool_calls_made=["query_facts", "query_graph"]
        )
        ```
    """

    answer: str = Field(
        min_length=1, description="Natural language response with inline citation links"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="List of citations for all sources referenced in the answer",
    )
    tool_calls_made: list[str] = Field(
        default_factory=list,
        description="List of tool names called during response generation (for debugging)",
    )


# Export all schemas for easy importing
__all__ = [
    "Citation",
    "ConversationResponse",
]
