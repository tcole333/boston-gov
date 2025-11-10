"""Unit tests for ConversationAgent with mocked LLM and services.

These tests verify that the ConversationAgent correctly answers the 5 core RPP
questions with proper citations, handles edge cases, and refuses inappropriate
requests.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import ContentBlock, Message, TextBlock, ToolUseBlock, Usage

from src.agents.conversation import ConversationAgent, ConversationAgentError
from src.schemas.agent import Citation, ConversationResponse
from src.schemas.facts import Fact
from src.schemas.graph import ConfidenceLevel, Office, Process, Requirement, Step
from src.services.facts_service import FactsService
from src.services.graph_service import GraphService


@pytest.fixture
def mock_graph_service():
    """Create a mock GraphService."""
    service = AsyncMock(spec=GraphService)

    # Mock process data
    service.get_process_by_id.return_value = Process(
        process_id="boston_resident_parking_permit",
        name="Boston Resident Parking Permit",
        category="permits",
        jurisdiction="City of Boston",
        description="Get a resident parking permit for your Boston neighborhood",
        source_url="https://www.boston.gov/departments/parking-clerk/resident-parking-permits",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
    )

    # Mock steps data
    service.get_process_steps.return_value = [
        Step(
            step_id="rpp_step_1_check_eligibility",
            process_id="boston_resident_parking_permit",
            name="Check Eligibility",
            description="Verify you meet all eligibility requirements",
            order=1,
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Step(
            step_id="rpp_step_2_gather_documents",
            process_id="boston_resident_parking_permit",
            name="Gather Documents",
            description="Collect required documents",
            order=2,
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Step(
            step_id="rpp_step_3_submit_application",
            process_id="boston_resident_parking_permit",
            name="Submit Application",
            description="Submit application in person or by mail",
            order=3,
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    # Mock requirements data
    service.get_process_requirements.return_value = [
        Requirement(
            requirement_id="rpp_req_ma_registration",
            text="Valid Massachusetts registration",
            fact_id="rpp.eligibility.registration_state",
            applies_to_process="boston_resident_parking_permit",
            hard_gate=True,
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Requirement(
            requirement_id="rpp_req_proof_of_residency",
            text="One proof of residency within 30 days",
            fact_id="rpp.proof_of_residency.count",
            applies_to_process="boston_resident_parking_permit",
            hard_gate=True,
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    # Mock office data
    service.get_step_office.return_value = Office(
        office_id="boston_parking_clerk",
        name="Office of the Parking Clerk",
        address="1 City Hall Square, Room 224, Boston MA 02201",
        phone="617-635-4410",
        email="parking@boston.gov",
        hours="Monday-Friday, 9:00 AM - 4:30 PM",
        source_url="https://www.boston.gov/departments/parking-clerk",
        last_verified=date(2025, 11, 9),
        confidence=ConfidenceLevel.HIGH,
    )

    return service


@pytest.fixture
def mock_facts_service():
    """Create a mock FactsService with sample facts."""
    service = MagicMock(spec=FactsService)

    # Sample facts for eligibility question
    eligibility_facts = [
        Fact(
            id="rpp.eligibility.vehicle_class",
            text="Eligible vehicles are passenger vehicles or commercial vehicles under 1 ton",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Vehicle eligibility",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.eligibility.registration_state",
            text="Vehicle must have valid Massachusetts registration in applicant's name at the Boston address, with principal garaging and insurance at that address",
            source_url="https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf",
            source_section="Section 15, Rule 15-4A",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.eligibility.no_unpaid_tickets",
            text="No unpaid Boston parking tickets on the registration",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Eligibility requirements",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    # Sample facts for documents question
    document_facts = [
        Fact(
            id="rpp.proof_of_residency.count",
            text="Exactly one proof of residency required",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Proof of Boston residency",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.proof_of_residency.recency",
            text="Proof of residency must be dated within 30 days",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Proof of Boston residency",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.proof_of_residency.accepted_types",
            text="Accepted proofs include utility bill (gas/electric/telephone), cable bill, bank statement, mortgage statement, credit card statement, water/sewer bill, or lease agreement",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Proof of Boston residency",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    # Sample facts for office location question
    office_facts = [
        Fact(
            id="rpp.office.location",
            text="Office of the Parking Clerk is located at 1 City Hall Square, Room 224, Boston MA 02201",
            source_url="https://www.boston.gov/departments/parking-clerk",
            source_section="Contact information",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.office.hours",
            text="Office hours are Monday-Friday, 9:00 AM - 4:30 PM",
            source_url="https://www.boston.gov/departments/parking-clerk",
            source_section="Contact information",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    # Sample facts for cost question
    cost_facts = [
        Fact(
            id="rpp.permit.cost",
            text="Resident parking permits are free",
            source_url="https://www.boston.gov/departments/parking-clerk/resident-parking-permits",
            source_section="Permit details",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
    ]

    # Sample facts for timing question
    timing_facts = [
        Fact(
            id="rpp.permit.in_person_timing",
            text="In-person applications at City Hall result in same-day permit issuance",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Application process",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        ),
        Fact(
            id="rpp.permit.mail_timing",
            text="Permits submitted by mail typically arrive in 5-10 business days",
            source_url="https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            source_section="Application process",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.MEDIUM,
            note="Timing is typical/observed, not guaranteed",
        ),
    ]

    # Configure mock responses based on prefix
    def get_facts_by_prefix_side_effect(prefix):
        if prefix == "rpp.eligibility":
            return eligibility_facts
        elif prefix == "rpp.proof_of_residency":
            return document_facts
        elif prefix == "rpp.office":
            return office_facts
        elif prefix == "rpp.permit.cost":
            return cost_facts
        elif prefix == "rpp.permit":
            return timing_facts
        else:
            return []

    service.get_facts_by_prefix.side_effect = get_facts_by_prefix_side_effect

    # Configure get_fact_by_id
    all_facts = eligibility_facts + document_facts + office_facts + cost_facts + timing_facts
    facts_dict = {fact.id: fact for fact in all_facts}

    def get_fact_by_id_side_effect(fact_id):
        return facts_dict.get(fact_id)

    service.get_fact_by_id.side_effect = get_fact_by_id_side_effect

    return service


@pytest.fixture
def agent(mock_graph_service, mock_facts_service):
    """Create a ConversationAgent with mocked services and Anthropic client."""
    with patch("src.agents.conversation.Anthropic") as mock_anthropic:
        # Create mock client instance
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Create agent
        agent = ConversationAgent(
            graph_service=mock_graph_service,
            facts_service=mock_facts_service,
            api_key="test-api-key",
        )

        # Store mock client on agent for test access
        agent._mock_client = mock_client

        yield agent


# ==================== Initialization Tests ====================


def test_agent_initialization(mock_graph_service, mock_facts_service):
    """Test ConversationAgent initializes properly."""
    agent = ConversationAgent(
        graph_service=mock_graph_service, facts_service=mock_facts_service, api_key="test-key"
    )
    assert agent.graph_service == mock_graph_service
    assert agent.facts_service == mock_facts_service
    assert agent.system_prompt is not None
    assert "citation" in agent.system_prompt.lower()


def test_agent_initialization_without_api_key(mock_graph_service, mock_facts_service):
    """Test agent raises error if no API key provided."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="api_key must be provided"):
            ConversationAgent(
                graph_service=mock_graph_service, facts_service=mock_facts_service, api_key=None
            )


def test_agent_initialization_with_env_var_api_key(mock_graph_service, mock_facts_service):
    """Test agent uses ANTHROPIC_API_KEY from environment."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-test-key"}):
        agent = ConversationAgent(
            graph_service=mock_graph_service, facts_service=mock_facts_service, api_key=None
        )
        assert agent.client is not None


# ==================== Tool Definition Tests ====================


def test_tool_definitions(agent):
    """Test that tools are properly defined."""
    tools = agent._define_tools()
    assert len(tools) == 2

    tool_names = [tool["name"] for tool in tools]
    assert "query_graph" in tool_names
    assert "query_facts" in tool_names

    # Verify query_graph schema
    query_graph_tool = next(t for t in tools if t["name"] == "query_graph")
    assert "input_schema" in query_graph_tool
    assert "query_type" in query_graph_tool["input_schema"]["properties"]

    # Verify query_facts schema
    query_facts_tool = next(t for t in tools if t["name"] == "query_facts")
    assert "input_schema" in query_facts_tool
    assert "query_type" in query_facts_tool["input_schema"]["properties"]


# ==================== Tool Execution Tests ====================


async def test_execute_graph_query_get_process(agent):
    """Test executing graph query for process."""
    result = await agent._execute_graph_query(
        {"query_type": "get_process", "process_id": "boston_resident_parking_permit"}
    )

    assert "process" in result
    assert result["process"]["process_id"] == "boston_resident_parking_permit"


async def test_execute_graph_query_get_steps(agent):
    """Test executing graph query for steps."""
    result = await agent._execute_graph_query(
        {"query_type": "get_process_steps", "process_id": "boston_resident_parking_permit"}
    )

    assert "steps" in result
    assert len(result["steps"]) == 3
    assert result["steps"][0]["order"] == 1


async def test_execute_facts_query_by_prefix(agent):
    """Test executing facts query by prefix."""
    result = await agent._execute_facts_query(
        {"query_type": "by_prefix", "prefix": "rpp.eligibility"}
    )

    assert "facts" in result
    assert len(result["facts"]) == 3
    assert all("rpp.eligibility" in fact["id"] for fact in result["facts"])


async def test_execute_facts_query_by_id(agent):
    """Test executing facts query by ID."""
    result = await agent._execute_facts_query({"query_type": "by_id", "fact_id": "rpp.permit.cost"})

    assert "fact" in result
    assert result["fact"]["id"] == "rpp.permit.cost"


async def test_execute_tool_call_unknown_tool(agent):
    """Test executing unknown tool returns error."""
    result = await agent._execute_tool_call("unknown_tool", {})

    assert "error" in result
    assert "Unknown tool" in result["message"]


# ==================== Core Question Tests (Issue #16) ====================


@pytest.mark.asyncio
async def test_question_1_eligibility(agent):
    """Test Q1: Am I eligible for a resident parking permit?"""
    # Mock LLM response with tool use then final answer
    agent._mock_client.messages.create.side_effect = [
        # First call: LLM requests query_facts tool
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_prefix", "prefix": "rpp.eligibility"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        # Second call: LLM provides final answer
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text='To be eligible for a resident parking permit, you must meet these requirements:\n\n1. Your vehicle must be a [passenger vehicle or commercial vehicle under 1 ton](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.eligibility.vehicle_class")\n2. You must have [valid Massachusetts registration in your name at your Boston address](https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf "rpp.eligibility.registration_state")\n3. You must have [no unpaid Boston parking tickets](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.eligibility.no_unpaid_tickets")',
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("Am I eligible for a resident parking permit?")

    assert isinstance(response, ConversationResponse)
    assert "Massachusetts registration" in response.answer
    assert "passenger vehicle" in response.answer
    assert len(response.citations) == 3
    assert any(c.fact_id == "rpp.eligibility.vehicle_class" for c in response.citations)
    assert "query_facts" in response.tool_calls_made


@pytest.mark.asyncio
async def test_question_2_documents(agent):
    """Test Q2: What documents do I need?"""
    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_prefix", "prefix": "rpp.proof_of_residency"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text='You need [exactly one proof of residency](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.proof_of_residency.count") that is [dated within 30 days](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.proof_of_residency.recency"). Accepted documents include utility bills, bank statements, or lease agreements.',
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("What documents do I need?")

    assert isinstance(response, ConversationResponse)
    assert "one proof of residency" in response.answer
    assert "30 days" in response.answer
    assert len(response.citations) >= 2
    assert any(c.fact_id == "rpp.proof_of_residency.count" for c in response.citations)


@pytest.mark.asyncio
async def test_question_3_office_location(agent):
    """Test Q3: Where is the office located?"""
    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_prefix", "prefix": "rpp.office"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text='The [Office of the Parking Clerk is located at 1 City Hall Square, Room 224, Boston MA 02201](https://www.boston.gov/departments/parking-clerk "rpp.office.location"). [Office hours are Monday-Friday, 9:00 AM - 4:30 PM](https://www.boston.gov/departments/parking-clerk "rpp.office.hours").',
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("Where is the office located?")

    assert isinstance(response, ConversationResponse)
    assert "City Hall Square" in response.answer or "1 City Hall" in response.answer
    assert len(response.citations) >= 1
    assert any(c.fact_id == "rpp.office.location" for c in response.citations)


@pytest.mark.asyncio
async def test_question_4_cost(agent):
    """Test Q4: How much does it cost?"""
    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_id", "fact_id": "rpp.permit.cost"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text='Good news! [Resident parking permits are free](https://www.boston.gov/departments/parking-clerk/resident-parking-permits "rpp.permit.cost").',
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("How much does it cost?")

    assert isinstance(response, ConversationResponse)
    assert "free" in response.answer.lower()
    assert len(response.citations) >= 1
    assert any(c.fact_id == "rpp.permit.cost" for c in response.citations)


@pytest.mark.asyncio
async def test_question_5_timing(agent):
    """Test Q5: How long does it take?"""
    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_prefix", "prefix": "rpp.permit"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text='The timing depends on how you apply:\n\n- [In-person at City Hall: same-day permit issuance](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.permit.in_person_timing")\n- [By mail: typically 5-10 business days](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.permit.mail_timing")\n\nNote: The mail timing is typical but not guaranteed.',
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("How long does it take?")

    assert isinstance(response, ConversationResponse)
    assert "same-day" in response.answer or "5-10" in response.answer
    assert len(response.citations) >= 1


# ==================== Edge Case Tests ====================


@pytest.mark.asyncio
async def test_legal_advice_refusal(agent):
    """Test that agent refuses to give legal advice."""
    agent._mock_client.messages.create.return_value = Message(
        id="msg_1",
        model="claude-sonnet-4-5-20250929",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text="I cannot provide legal advice. For legal questions about parking tickets or violations, I recommend consulting with an attorney or contacting the Parking Clerk's office directly.",
            )
        ],
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
        type="message",
    )

    response = await agent.ask("Can I sue the city if I get a ticket?")

    assert isinstance(response, ConversationResponse)
    assert "cannot provide legal advice" in response.answer or "consult" in response.answer.lower()


@pytest.mark.asyncio
async def test_ambiguous_question(agent):
    """Test handling of ambiguous questions."""
    agent._mock_client.messages.create.return_value = Message(
        id="msg_1",
        model="claude-sonnet-4-5-20250929",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text="I'm not sure what specific information you need. Are you asking about eligibility requirements, required documents, application process, or something else? Please clarify so I can provide accurate cited information.",
            )
        ],
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
        type="message",
    )

    response = await agent.ask("What about parking?")

    assert isinstance(response, ConversationResponse)
    assert len(response.answer) > 0


@pytest.mark.asyncio
async def test_graph_service_error_handling(agent):
    """Test graceful error handling when GraphService fails."""
    agent.graph_service.get_process_by_id.side_effect = Exception("Database connection failed")

    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_graph",
                    input={
                        "query_type": "get_process",
                        "process_id": "boston_resident_parking_permit",
                    },
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text="I encountered an error accessing the process information. Please try again later or contact the office directly.",
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("Tell me about the RPP process")

    assert isinstance(response, ConversationResponse)
    # Should still return a response even if tool failed


@pytest.mark.asyncio
async def test_max_iterations_error(agent):
    """Test that max iterations prevents infinite loops."""
    # Mock LLM to keep requesting tools
    agent._mock_client.messages.create.return_value = Message(
        id="msg_1",
        model="claude-sonnet-4-5-20250929",
        role="assistant",
        content=[
            ToolUseBlock(
                id="tool_1",
                type="tool_use",
                name="query_facts",
                input={"query_type": "by_prefix", "prefix": "rpp.eligibility"},
            )
        ],
        stop_reason="tool_use",
        usage=Usage(input_tokens=100, output_tokens=50),
        type="message",
    )

    with pytest.raises(ConversationAgentError, match="Max iterations"):
        await agent.ask("Test question", max_iterations=2)


@pytest.mark.asyncio
async def test_combined_graph_and_facts_query(agent):
    """Test questions requiring both graph and facts queries."""
    agent._mock_client.messages.create.side_effect = [
        Message(
            id="msg_1",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_1",
                    type="tool_use",
                    name="query_graph",
                    input={
                        "query_type": "get_process_steps",
                        "process_id": "boston_resident_parking_permit",
                    },
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=100, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_2",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                ToolUseBlock(
                    id="tool_2",
                    type="tool_use",
                    name="query_facts",
                    input={"query_type": "by_prefix", "prefix": "rpp.eligibility"},
                )
            ],
            stop_reason="tool_use",
            usage=Usage(input_tokens=150, output_tokens=50),
            type="message",
        ),
        Message(
            id="msg_3",
            model="claude-sonnet-4-5-20250929",
            role="assistant",
            content=[
                TextBlock(
                    type="text",
                    text="The process has 3 steps. First, check eligibility requirements...",
                )
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=200, output_tokens=100),
            type="message",
        ),
    ]

    response = await agent.ask("What are the steps and requirements?")

    assert isinstance(response, ConversationResponse)
    assert "query_graph" in response.tool_calls_made
    assert "query_facts" in response.tool_calls_made


# ==================== Citation Extraction Tests ====================


def test_extract_citations_from_tool_results(agent):
    """Test citation extraction from tool results."""
    tool_results = [
        {
            "fact": {
                "id": "rpp.permit.cost",
                "text": "Resident parking permits are free",
                "source_url": "https://www.boston.gov/departments/parking-clerk/resident-parking-permits",
                "source_section": "Permit details",
            }
        },
        {
            "facts": [
                {
                    "id": "rpp.eligibility.vehicle_class",
                    "text": "Eligible vehicles are passenger vehicles",
                    "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                    "source_section": "Vehicle eligibility",
                }
            ]
        },
    ]

    citations = agent._extract_citations_from_response("test response", tool_results)

    assert len(citations) == 2
    assert citations[0].fact_id == "rpp.permit.cost"
    assert citations[1].fact_id == "rpp.eligibility.vehicle_class"


def test_extract_citations_deduplication(agent):
    """Test that duplicate citations are not included."""
    tool_results = [
        {
            "fact": {
                "id": "rpp.permit.cost",
                "text": "Resident parking permits are free",
                "source_url": "https://www.boston.gov/test",
                "source_section": None,
            }
        },
        {
            "fact": {
                "id": "rpp.permit.cost",  # Duplicate
                "text": "Resident parking permits are free",
                "source_url": "https://www.boston.gov/test",
                "source_section": None,
            }
        },
    ]

    citations = agent._extract_citations_from_response("test", tool_results)

    assert len(citations) == 1


# ==================== System Prompt Tests ====================


def test_system_prompt_contains_citation_requirements(agent):
    """Test that system prompt includes citation requirements."""
    prompt = agent.system_prompt

    assert "citation" in prompt.lower()
    assert "fact" in prompt.lower()
    assert "source" in prompt.lower()


def test_system_prompt_contains_refusal_guidance(agent):
    """Test that system prompt includes guidance on refusals."""
    prompt = agent.system_prompt

    assert "legal advice" in prompt.lower()
    assert "refuse" in prompt.lower() or "politely" in prompt.lower()
