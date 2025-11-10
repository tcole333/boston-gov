"""Conversation agent for answering RPP questions with citations.

This module implements the core conversation agent using the Anthropic Claude SDK.
It uses native tool calling to query the Neo4j graph and Facts Registry, ensuring
all responses are properly cited with traceable sources.

Usage:
    ```python
    from src.agents.conversation import ConversationAgent
    from src.services.graph_service import get_graph_service
    from src.services.facts_service import get_facts_service
    import os

    graph_service = get_graph_service()
    facts_service = get_facts_service()
    facts_service.load_registry("boston_rpp")

    agent = ConversationAgent(
        graph_service=graph_service,
        facts_service=facts_service,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    response = agent.ask("Am I eligible for a resident parking permit?")
    print(response.answer)
    for citation in response.citations:
        print(f"- {citation.text} ({citation.url})")
    ```
"""

import logging
import os
from typing import Any

from anthropic import Anthropic
from anthropic.types import Message, MessageParam, TextBlock, ToolUseBlock

from src.schemas.agent import Citation, ConversationResponse
from src.services.facts_service import FactsService
from src.services.graph_service import GraphService

logger = logging.getLogger(__name__)

# Model to use for conversation
MODEL = "claude-sonnet-4-5-20250929"


class ConversationAgentError(Exception):
    """Base exception for conversation agent errors."""

    pass


class ConversationAgent:
    """
    Conversation agent for answering RPP questions with citations.

    This agent uses Anthropic Claude SDK with native tool calling to query
    the Neo4j graph and Facts Registry. All regulatory claims are cited
    with traceable sources from the Facts Registry.

    Attributes:
        graph_service: GraphService instance for querying Neo4j
        facts_service: FactsService instance for querying Facts Registry
        client: Anthropic SDK client
        system_prompt: System prompt with citation requirements and guidelines
    """

    def __init__(
        self, graph_service: GraphService, facts_service: FactsService, api_key: str | None = None
    ) -> None:
        """
        Initialize the conversation agent.

        Args:
            graph_service: GraphService instance for querying Neo4j
            facts_service: FactsService instance for Facts Registry lookups
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)

        Raises:
            ValueError: If api_key is None and ANTHROPIC_API_KEY is not set
        """
        self.graph_service = graph_service
        self.facts_service = facts_service

        # Initialize Anthropic client
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "api_key must be provided or ANTHROPIC_API_KEY environment variable must be set"
                )

        self.client = Anthropic(api_key=api_key)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt with citation requirements and guidelines.

        Returns:
            System prompt string with instructions for the agent
        """
        return """You are a helpful assistant for Boston residents navigating government processes, starting with the Resident Parking Permit (RPP) program.

**CRITICAL CITATION REQUIREMENTS:**
- You MUST cite ALL regulatory claims using the Facts Registry
- Use the query_facts tool to look up regulatory facts before making claims
- Use the query_graph tool to look up process structure, steps, and requirements
- NEVER make unsourced regulatory claims or speculate
- If you cannot find a source, say "I don't have verified information about that"

**RESPONSE FORMAT:**
- Use inline citations: [claim text](source_url "fact_id")
- Example: "You need [one proof of residency within 30 days](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit "rpp.proof_of_residency.recency")"
- Always provide the fact_id in the citation link title (in quotes)

**TONE AND STYLE:**
- Professional, helpful, and government-appropriate
- Clear and concise
- Adaptive to the user's level of understanding
- Empathetic to bureaucratic challenges

**WHAT TO REFUSE:**
- Legal advice (politely suggest consulting an attorney)
- Medical advice
- Speculation without sources
- Making guarantees about outcomes ("you will definitely qualify")
- Advice that contradicts official regulations

**HOW TO USE TOOLS:**
1. For questions about eligibility, requirements, costs, timing, or procedures:
   - First use query_facts to get regulatory facts
   - Use query_graph to understand process structure if needed
2. For questions about office locations, hours, or contact info:
   - Use query_facts (office info is in Facts Registry)
   - Use query_graph to find office relationships if needed
3. For questions about process steps or dependencies:
   - Use query_graph to get process steps
   - Use query_facts to get detailed requirements for each step

**CONFIDENCE CALIBRATION:**
- If a fact has "medium" or "low" confidence, mention this to the user
- If requirements are ambiguous, acknowledge the ambiguity
- When in doubt, direct users to call the office or check the official website

Remember: Your primary value is providing **cited, traceable, accurate** information. It's better to say "I don't know" than to provide unsourced claims."""

    def _define_tools(self) -> list[dict[str, Any]]:
        """
        Define tool schemas for Anthropic SDK native tool calling.

        Returns:
            List of tool definitions in Anthropic SDK format
        """
        return [
            {
                "name": "query_graph",
                "description": "Query the Neo4j graph database for process structure, steps, requirements, offices, and document types. Use this to understand the process flow, dependencies, and what entities are involved.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": [
                                "get_process",
                                "get_process_steps",
                                "get_process_requirements",
                                "get_step_office",
                                "get_step_documents",
                                "get_requirement_documents",
                            ],
                            "description": "Type of graph query to execute",
                        },
                        "process_id": {
                            "type": "string",
                            "description": "Process identifier (e.g., 'boston_resident_parking_permit'). Required for process queries.",
                        },
                        "step_id": {
                            "type": "string",
                            "description": "Step identifier. Required for step queries.",
                        },
                        "requirement_id": {
                            "type": "string",
                            "description": "Requirement identifier. Required for requirement queries.",
                        },
                    },
                    "required": ["query_type"],
                },
            },
            {
                "name": "query_facts",
                "description": "Query the Facts Registry for verified regulatory facts. Use this to get cited information about eligibility, requirements, costs, timing, office info, and all regulatory details. ALL regulatory claims must come from this registry.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["by_id", "by_prefix", "all"],
                            "description": "Type of facts query: by_id (specific fact), by_prefix (category), or all (all loaded facts)",
                        },
                        "fact_id": {
                            "type": "string",
                            "description": "Specific fact ID to retrieve. Required when query_type is 'by_id'. Example: 'rpp.eligibility.vehicle_class'",
                        },
                        "prefix": {
                            "type": "string",
                            "description": "Fact ID prefix to match. Required when query_type is 'by_prefix'. Example: 'rpp.eligibility' to get all eligibility facts.",
                        },
                    },
                    "required": ["query_type"],
                },
            },
        ]

    async def _execute_tool_call(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a tool call (query_graph or query_facts).

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Dictionary with tool execution results

        Raises:
            ConversationAgentError: If tool execution fails
        """
        try:
            if tool_name == "query_graph":
                return await self._execute_graph_query(tool_input)
            elif tool_name == "query_facts":
                return await self._execute_facts_query(tool_input)
            else:
                raise ConversationAgentError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            # Sanitize error message to avoid leaking internal details to LLM
            sanitized_message = (
                "Tool execution failed due to an internal error. "
                "Please try rephrasing your query or contact support if the issue persists."
            )
            return {
                "error": "internal_error",
                "tool": tool_name,
                "message": sanitized_message,
            }

    async def _execute_graph_query(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a graph query using GraphService.

        Args:
            tool_input: Query parameters including query_type and relevant IDs

        Returns:
            Dictionary with query results
        """
        query_type = tool_input.get("query_type")
        if not query_type:
            return {"error": "Missing required parameter: query_type"}

        if query_type == "get_process":
            process_id = tool_input.get("process_id")
            if not process_id:
                return {"error": "Missing required parameter: process_id"}
            process = await self.graph_service.get_process_by_id(process_id)
            return {"process": process.model_dump() if process else None}

        elif query_type == "get_process_steps":
            process_id = tool_input.get("process_id")
            if not process_id:
                return {"error": "Missing required parameter: process_id"}
            steps = await self.graph_service.get_process_steps(process_id)
            return {"steps": [step.model_dump() for step in steps]}

        elif query_type == "get_process_requirements":
            process_id = tool_input.get("process_id")
            if not process_id:
                return {"error": "Missing required parameter: process_id"}
            requirements = await self.graph_service.get_process_requirements(process_id)
            return {"requirements": [req.model_dump() for req in requirements]}

        elif query_type == "get_step_office":
            step_id = tool_input.get("step_id")
            if not step_id:
                return {"error": "Missing required parameter: step_id"}
            office = await self.graph_service.get_step_office(step_id)
            return {"office": office.model_dump() if office else None}

        elif query_type == "get_step_documents":
            step_id = tool_input.get("step_id")
            if not step_id:
                return {"error": "Missing required parameter: step_id"}
            docs = await self.graph_service.get_step_document_types(step_id)
            return {"documents": [doc.model_dump() for doc in docs]}

        elif query_type == "get_requirement_documents":
            requirement_id = tool_input.get("requirement_id")
            if not requirement_id:
                return {"error": "Missing required parameter: requirement_id"}
            docs = await self.graph_service.get_requirement_document_types(requirement_id)
            return {"documents": [doc.model_dump() for doc in docs]}

        else:
            return {"error": f"Unknown query_type: {query_type}"}

    async def _execute_facts_query(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a facts query using FactsService.

        Args:
            tool_input: Query parameters including query_type and optional fact_id/prefix

        Returns:
            Dictionary with query results
        """
        query_type = tool_input.get("query_type")
        if not query_type:
            return {"error": "Missing required parameter: query_type"}

        if query_type == "by_id":
            fact_id = tool_input.get("fact_id")
            if not fact_id:
                return {"error": "Missing required parameter: fact_id"}
            fact = self.facts_service.get_fact_by_id(fact_id)
            return {"fact": fact.model_dump() if fact else None}

        elif query_type == "by_prefix":
            prefix = tool_input.get("prefix")
            if not prefix:
                return {"error": "Missing required parameter: prefix"}
            facts = self.facts_service.get_facts_by_prefix(prefix)
            return {"facts": [fact.model_dump() for fact in facts]}

        elif query_type == "all":
            facts = self.facts_service.get_all_facts()
            return {"facts": [fact.model_dump() for fact in facts]}

        else:
            return {"error": f"Unknown query_type: {query_type}"}

    def _extract_citations_from_response(
        self, response_text: str, tool_results: list[dict[str, Any]]
    ) -> list[Citation]:
        """
        Extract citations from tool results.

        This method parses the tool results to extract all facts that were
        used in the response and creates Citation objects.

        Args:
            response_text: The response text (may contain citation references)
            tool_results: List of tool execution results

        Returns:
            List of Citation objects
        """
        citations: list[Citation] = []
        seen_fact_ids: set[str] = set()

        for result in tool_results:
            # Extract facts from query_facts results
            if "fact" in result and result["fact"]:
                fact_data = result["fact"]
                fact_id = fact_data.get("id")
                # Validate required fields exist
                if not fact_id or "source_url" not in fact_data or "text" not in fact_data:
                    logger.warning(f"Skipping malformed fact data: {fact_data}")
                    continue
                if fact_id not in seen_fact_ids:
                    citations.append(
                        Citation(
                            fact_id=fact_id,
                            url=fact_data["source_url"],
                            text=fact_data["text"],
                            source_section=fact_data.get("source_section"),
                        )
                    )
                    seen_fact_ids.add(fact_id)

            elif "facts" in result and result["facts"]:
                for fact_data in result["facts"]:
                    fact_id = fact_data.get("id")
                    # Validate required fields exist
                    if not fact_id or "source_url" not in fact_data or "text" not in fact_data:
                        logger.warning(f"Skipping malformed fact data: {fact_data}")
                        continue
                    if fact_id not in seen_fact_ids:
                        citations.append(
                            Citation(
                                fact_id=fact_id,
                                url=fact_data["source_url"],
                                text=fact_data["text"],
                                source_section=fact_data.get("source_section"),
                            )
                        )
                        seen_fact_ids.add(fact_id)

        return citations

    async def ask(self, question: str, max_iterations: int = 5) -> ConversationResponse:
        """
        Ask a question and get a cited response.

        This is the main entry point for the conversation agent. It uses
        Anthropic's native tool calling to execute multiple tool calls as needed,
        then returns a properly formatted and cited response.

        Args:
            question: User's question about RPP or government processes
            max_iterations: Maximum number of tool calling iterations (default: 5)

        Returns:
            ConversationResponse with answer, citations, and metadata

        Raises:
            ConversationAgentError: If the agent fails to generate a response
            ValueError: If question is empty or max_iterations is out of range

        Examples:
            ```python
            response = await agent.ask("Am I eligible for a resident parking permit?")
            print(response.answer)
            # Output: "To be eligible for a resident parking permit, you must..."
            ```
        """
        # Validate question
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        if len(question) > 10000:
            raise ValueError("Question exceeds maximum length of 10000 characters")
        question = question.strip()

        # Validate max_iterations
        if not isinstance(max_iterations, int) or max_iterations < 1 or max_iterations > 20:
            raise ValueError("max_iterations must be an integer between 1 and 20")

        try:
            tools = self._define_tools()
            messages: list[MessageParam] = [{"role": "user", "content": question}]
            tool_results: list[dict[str, Any]] = []
            tool_calls_made: list[str] = []

            # Tool calling loop
            for iteration in range(max_iterations):
                logger.debug(f"Iteration {iteration + 1}: Calling Claude API")

                response: Message = self.client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=tools,  # type: ignore
                    messages=messages,
                )

                # Check if we're done (no more tool calls)
                tool_use_blocks = [
                    block for block in response.content if isinstance(block, ToolUseBlock)
                ]

                if not tool_use_blocks:
                    # Extract final text response
                    text_blocks = [
                        block for block in response.content if isinstance(block, TextBlock)
                    ]
                    if text_blocks:
                        answer = "".join(block.text for block in text_blocks)

                        # Extract citations from all tool results
                        citations = self._extract_citations_from_response(answer, tool_results)

                        return ConversationResponse(
                            answer=answer, citations=citations, tool_calls_made=tool_calls_made
                        )
                    else:
                        raise ConversationAgentError("No text response from agent")

                # Execute tool calls
                tool_response_content = []
                for tool_use in tool_use_blocks:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_calls_made.append(tool_name)

                    logger.debug(f"Executing tool: {tool_name} with input: {tool_input}")

                    # Execute the tool
                    result = await self._execute_tool_call(tool_name, tool_input)
                    tool_results.append(result)

                    # Add tool result to message history
                    tool_response_content.append(
                        {"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}
                    )

                # Add assistant message and tool results to history
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_response_content})  # type: ignore[typeddict-item]

            # If we hit max iterations, return what we have
            raise ConversationAgentError(
                f"Max iterations ({max_iterations}) reached without final response"
            )

        except ConversationAgentError:
            raise
        except Exception as e:
            logger.error(f"Error in conversation agent: {e}")
            raise ConversationAgentError(f"Failed to generate response: {e}") from e


def get_conversation_agent(
    graph_service: GraphService | None = None,
    facts_service: FactsService | None = None,
    api_key: str | None = None,
) -> ConversationAgent:
    """
    Factory function to create a ConversationAgent instance.

    This is useful for dependency injection in FastAPI routes.

    Args:
        graph_service: Optional GraphService instance (creates new one if None)
        facts_service: Optional FactsService instance (creates new one if None)
        api_key: Optional Anthropic API key (uses env var if None)

    Returns:
        ConversationAgent instance

    Example:
        ```python
        from fastapi import Depends
        from src.agents.conversation import get_conversation_agent, ConversationAgent

        @app.post("/ask")
        async def ask_question(
            question: str,
            agent: ConversationAgent = Depends(get_conversation_agent)
        ):
            response = await agent.ask(question)
            return response
        ```
    """
    if graph_service is None:
        from src.services.graph_service import get_graph_service

        graph_service = get_graph_service()

    if facts_service is None:
        from src.services.facts_service import get_facts_service

        facts_service = get_facts_service()
        # Load the boston_rpp registry by default
        facts_service.load_registry("boston_rpp")

    return ConversationAgent(
        graph_service=graph_service, facts_service=facts_service, api_key=api_key
    )
