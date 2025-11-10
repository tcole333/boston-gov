"""REST API endpoints for chat interactions.

This module provides endpoints for:
- Sending chat messages and receiving agent responses with citations

All endpoints use the ConversationAgent for answering questions about
Boston government processes (starting with Resident Parking Permits).
Responses are properly cited with traceable sources from the Facts Registry.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.agents.conversation import (
    ConversationAgent,
    ConversationAgentError,
    get_conversation_agent,
)
from src.schemas.agent import ConversationResponse
from src.services.graph_service import ConnectionError

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request schema for chat endpoint.

    Attributes:
        message: User's question or message (1-10000 characters)
        session_id: Optional session identifier for future session management
                   (not used in MVP, stateless design)

    Examples:
        ```json
        {
            "message": "Am I eligible for a resident parking permit?",
            "session_id": null
        }
        ```
    """

    message: str = Field(
        min_length=1,
        max_length=10000,
        description="User's question or message (1-10000 characters)",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier (not used in MVP)",
    )


def get_conversation_agent_dependency() -> ConversationAgent:
    """
    Dependency function to get a ConversationAgent instance.

    This is a wrapper around get_conversation_agent that works with FastAPI's
    dependency injection system. It handles initialization of GraphService,
    FactsService, and Anthropic API client.

    Returns:
        ConversationAgent instance configured with all required services

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set in environment
    """
    return get_conversation_agent()


# Create router with prefix and tags
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ConversationResponse)
async def send_message(
    request: ChatRequest,
    agent: ConversationAgent = Depends(get_conversation_agent_dependency),
) -> ConversationResponse:
    """
    Send a chat message and receive an agent response with citations.

    This endpoint accepts a user question about Boston government processes
    (starting with Resident Parking Permits) and returns a properly cited
    response from the conversation agent.

    The agent uses tool calling to query the Neo4j graph and Facts Registry,
    ensuring all regulatory claims are traceable to official sources.

    Args:
        request: ChatRequest with user message and optional session_id
        agent: ConversationAgent instance (injected)

    Returns:
        ConversationResponse with:
        - answer: Natural language response with inline citation links
        - citations: List of Citation objects for all sources referenced
        - tool_calls_made: List of tools used (for debugging)

    Raises:
        HTTPException: 400 if message is invalid (caught by Pydantic validation)
        HTTPException: 500 if agent fails to generate response
        HTTPException: 503 if service is unavailable (database, API errors)

    Examples:
        Request:
        ```json
        {
            "message": "Am I eligible for a resident parking permit?"
        }
        ```

        Response:
        ```json
        {
            "answer": "To be eligible for a resident parking permit, you must...",
            "citations": [
                {
                    "fact_id": "rpp.eligibility.vehicle_class",
                    "url": "https://www.boston.gov/...",
                    "text": "Vehicle must be a passenger vehicle or motorcycle",
                    "source_section": "Eligibility Requirements"
                }
            ],
            "tool_calls_made": ["query_facts", "query_graph"]
        }
        ```

    Note:
        - Session management is not implemented in MVP (stateless design)
        - session_id in request is accepted but not used
        - Returns 200 even for "I don't know" responses (per Issue #17)
    """
    try:
        # Call the conversation agent
        logger.info(f"Processing chat message (length: {len(request.message)})")
        response = await agent.ask(request.message)
        logger.info(
            f"Generated response with {len(response.citations)} citations, "
            f"{len(response.tool_calls_made)} tool calls"
        )
        return response

    except ValueError as e:
        # Validation errors from agent (empty message, invalid length, etc.)
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except ConnectionError as e:
        # Database connection errors
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later.",
        ) from e

    except ConversationAgentError as e:
        # Agent-specific errors (tool execution, LLM API errors, etc.)
        logger.error(f"Agent error: {e}")
        # Check if it's an API connectivity issue
        error_str = str(e).lower()
        if any(
            keyword in error_str for keyword in ["connection", "timeout", "unavailable", "network"]
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later.",
            ) from e
        else:
            # Generic agent error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response. Please try again or rephrase your question.",
            ) from e

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        ) from e
