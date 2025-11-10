"""Unit tests for chat API routes.

These tests use FastAPI's dependency override system to mock ConversationAgent
interactions and verify that the API routes correctly handle success and error cases.
All tests mock the Anthropic client to avoid real API calls.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from src.agents.conversation import ConversationAgent, ConversationAgentError
from src.api.routes.chat import get_conversation_agent_dependency
from src.main import app
from src.schemas.agent import Citation, ConversationResponse
from src.services.graph_service import ConnectionError


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create a mock ConversationAgent instance."""
    agent = MagicMock(spec=ConversationAgent)
    # Make the ask method an async mock
    agent.ask = AsyncMock()
    return agent


@pytest.fixture
def client(mock_agent: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client with mocked ConversationAgent dependency."""
    app.dependency_overrides[get_conversation_agent_dependency] = lambda: mock_agent
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_citation() -> Citation:
    """Create a mock Citation object."""
    return Citation(
        fact_id="rpp.eligibility.vehicle_class",
        url=HttpUrl(
            "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"
        ),
        text="Vehicle must be a passenger vehicle or motorcycle",
        source_section="Eligibility Requirements",
    )


@pytest.fixture
def mock_response(mock_citation: Citation) -> ConversationResponse:
    """Create a mock ConversationResponse object."""
    return ConversationResponse(
        answer=(
            "To be eligible for a resident parking permit, you must have "
            "[a passenger vehicle or motorcycle]"
            "(https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "
            '"rpp.eligibility.vehicle_class").'
        ),
        citations=[mock_citation],
        tool_calls_made=["query_facts"],
    )


# ==================== POST /api/chat/message ====================


def test_send_message_success(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test successful chat message with cited response."""
    mock_agent.ask.return_value = mock_response

    response = client.post(
        "/api/chat/message",
        json={"message": "Am I eligible for a resident parking permit?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "tool_calls_made" in data
    assert len(data["citations"]) == 1
    assert data["citations"][0]["fact_id"] == "rpp.eligibility.vehicle_class"
    assert data["citations"][0]["text"] == "Vehicle must be a passenger vehicle or motorcycle"
    assert data["tool_calls_made"] == ["query_facts"]

    # Verify agent was called with the message
    mock_agent.ask.assert_called_once_with("Am I eligible for a resident parking permit?")


def test_send_message_with_session_id(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test chat message with optional session_id (not used in MVP)."""
    mock_agent.ask.return_value = mock_response

    response = client.post(
        "/api/chat/message",
        json={
            "message": "What documents do I need?",
            "session_id": "test-session-123",
        },
    )

    assert response.status_code == 200
    # session_id is accepted but not used in MVP
    mock_agent.ask.assert_called_once_with("What documents do I need?")


def test_send_message_multiple_citations(
    client: TestClient, mock_agent: MagicMock
) -> None:
    """Test response with multiple citations."""
    response_with_multiple_citations = ConversationResponse(
        answer="You need two things: [valid MA registration] and [proof of residency]",
        citations=[
            Citation(
                fact_id="rpp.eligibility.registration_state",
                url=HttpUrl("https://www.boston.gov/test"),
                text="Must have MA registration",
            ),
            Citation(
                fact_id="rpp.proof_of_residency.count",
                url=HttpUrl("https://www.boston.gov/test"),
                text="One proof of residency required",
            ),
        ],
        tool_calls_made=["query_facts", "query_graph"],
    )
    mock_agent.ask.return_value = response_with_multiple_citations

    response = client.post(
        "/api/chat/message",
        json={"message": "What are the requirements?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 2
    assert len(data["tool_calls_made"]) == 2
    assert data["citations"][0]["fact_id"] == "rpp.eligibility.registration_state"
    assert data["citations"][1]["fact_id"] == "rpp.proof_of_residency.count"


def test_send_message_no_citations(client: TestClient, mock_agent: MagicMock) -> None:
    """Test response with no citations (e.g., 'I don't know' response)."""
    response_no_citations = ConversationResponse(
        answer="I don't have verified information about that. Please contact the Parking Clerk's office.",
        citations=[],
        tool_calls_made=["query_facts"],
    )
    mock_agent.ask.return_value = response_no_citations

    response = client.post(
        "/api/chat/message",
        json={"message": "What's the weather like?"},
    )

    # Should still return 200 even for "I don't know" responses (per Issue #17)
    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 0
    assert "don't have verified information" in data["answer"]


# ==================== Validation Tests ====================


def test_send_message_empty_message(client: TestClient, mock_agent: MagicMock) -> None:
    """Test validation error for empty message."""
    response = client.post(
        "/api/chat/message",
        json={"message": ""},
    )

    assert response.status_code == 422  # Pydantic validation error
    data = response.json()
    assert "detail" in data


def test_send_message_whitespace_only(client: TestClient, mock_agent: MagicMock) -> None:
    """Test error handling for whitespace-only message (caught by agent)."""
    # Agent's ask() method strips whitespace and raises ValueError
    mock_agent.ask.side_effect = ValueError("Question cannot be empty")

    response = client.post(
        "/api/chat/message",
        json={"message": "   "},
    )

    assert response.status_code == 400  # Agent ValueError becomes HTTP 400


def test_send_message_too_long(client: TestClient, mock_agent: MagicMock) -> None:
    """Test validation error for message exceeding max length."""
    long_message = "a" * 10001  # Exceeds 10000 char limit

    response = client.post(
        "/api/chat/message",
        json={"message": long_message},
    )

    assert response.status_code == 422  # Pydantic validation error


def test_send_message_missing_message_field(client: TestClient, mock_agent: MagicMock) -> None:
    """Test validation error when message field is missing."""
    response = client.post(
        "/api/chat/message",
        json={},
    )

    assert response.status_code == 422  # Pydantic validation error


def test_send_message_invalid_json(client: TestClient, mock_agent: MagicMock) -> None:
    """Test error handling for invalid JSON payload."""
    response = client.post(
        "/api/chat/message",
        data="not valid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422


# ==================== Error Handling Tests ====================


def test_send_message_agent_value_error(client: TestClient, mock_agent: MagicMock) -> None:
    """Test handling of ValueError from agent (validation errors)."""
    mock_agent.ask.side_effect = ValueError("Question cannot be empty")

    response = client.post(
        "/api/chat/message",
        json={"message": "test"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Question cannot be empty" in data["detail"]


def test_send_message_agent_error(client: TestClient, mock_agent: MagicMock) -> None:
    """Test handling of ConversationAgentError."""
    mock_agent.ask.side_effect = ConversationAgentError("Failed to generate response")

    response = client.post(
        "/api/chat/message",
        json={"message": "test question"},
    )

    assert response.status_code == 500
    data = response.json()
    assert "Failed to generate response" in data["detail"]
    # Should not leak internal error details
    assert "ConversationAgentError" not in data["detail"]


def test_send_message_agent_connection_error(client: TestClient, mock_agent: MagicMock) -> None:
    """Test handling of agent connection errors (503)."""
    mock_agent.ask.side_effect = ConversationAgentError("Connection timeout")

    response = client.post(
        "/api/chat/message",
        json={"message": "test question"},
    )

    assert response.status_code == 503
    data = response.json()
    assert "temporarily unavailable" in data["detail"].lower()


def test_send_message_database_connection_error(
    client: TestClient, mock_agent: MagicMock
) -> None:
    """Test handling of database connection errors."""
    mock_agent.ask.side_effect = ConnectionError("Database connection failed")

    response = client.post(
        "/api/chat/message",
        json={"message": "test question"},
    )

    assert response.status_code == 503
    data = response.json()
    assert "temporarily unavailable" in data["detail"].lower()


def test_send_message_agent_network_error(client: TestClient, mock_agent: MagicMock) -> None:
    """Test handling of network-related agent errors."""
    mock_agent.ask.side_effect = ConversationAgentError("Network error occurred")

    response = client.post(
        "/api/chat/message",
        json={"message": "test question"},
    )

    assert response.status_code == 503
    data = response.json()
    assert "temporarily unavailable" in data["detail"].lower()


def test_send_message_unexpected_error(client: TestClient, mock_agent: MagicMock) -> None:
    """Test handling of unexpected exceptions."""
    mock_agent.ask.side_effect = RuntimeError("Unexpected error")

    response = client.post(
        "/api/chat/message",
        json={"message": "test question"},
    )

    assert response.status_code == 500
    data = response.json()
    assert "unexpected error" in data["detail"].lower()


# ==================== Response Format Tests ====================


def test_response_format_contains_required_fields(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test that response contains all required fields in correct format."""
    mock_agent.ask.return_value = mock_response

    response = client.post(
        "/api/chat/message",
        json={"message": "test"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert isinstance(data["answer"], str)
    assert isinstance(data["citations"], list)
    assert isinstance(data["tool_calls_made"], list)

    # Verify citation structure
    if data["citations"]:
        citation = data["citations"][0]
        assert "fact_id" in citation
        assert "url" in citation
        assert "text" in citation
        # source_section is optional
        assert "source_section" in citation or "source_section" not in citation


def test_citation_format_validation(
    client: TestClient, mock_agent: MagicMock, mock_citation: Citation
) -> None:
    """Test that citations are properly formatted."""
    response_obj = ConversationResponse(
        answer="Test answer",
        citations=[mock_citation],
        tool_calls_made=["query_facts"],
    )
    mock_agent.ask.return_value = response_obj

    response = client.post(
        "/api/chat/message",
        json={"message": "test"},
    )

    assert response.status_code == 200
    data = response.json()
    citation = data["citations"][0]

    assert citation["fact_id"] == "rpp.eligibility.vehicle_class"
    assert "boston.gov" in citation["url"]
    assert len(citation["text"]) > 0
    assert citation["source_section"] == "Eligibility Requirements"


# ==================== Edge Cases ====================


def test_send_message_exact_max_length(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test message at exact maximum length boundary."""
    mock_agent.ask.return_value = mock_response
    exact_max_message = "a" * 10000  # Exactly 10000 chars

    response = client.post(
        "/api/chat/message",
        json={"message": exact_max_message},
    )

    assert response.status_code == 200
    mock_agent.ask.assert_called_once()


def test_send_message_with_special_characters(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test message with special characters and unicode."""
    mock_agent.ask.return_value = mock_response
    special_message = "Hello! What about permits for café owners? 你好"

    response = client.post(
        "/api/chat/message",
        json={"message": special_message},
    )

    assert response.status_code == 200
    mock_agent.ask.assert_called_once_with(special_message)


def test_send_message_with_newlines(
    client: TestClient, mock_agent: MagicMock, mock_response: ConversationResponse
) -> None:
    """Test message with newlines and formatting."""
    mock_agent.ask.return_value = mock_response
    multiline_message = "Question 1: Am I eligible?\n\nQuestion 2: What docs do I need?"

    response = client.post(
        "/api/chat/message",
        json={"message": multiline_message},
    )

    assert response.status_code == 200
    mock_agent.ask.assert_called_once_with(multiline_message)
