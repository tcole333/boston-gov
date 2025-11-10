"""Graph query service layer for Neo4j operations.

This module provides a service layer that abstracts Neo4j Cypher queries
and returns typed Pydantic models. It handles querying processes, steps,
requirements, documents, and related entities from the government process graph.

Usage:
    ```python
    from src.services.graph_service import GraphService
    from src.db.graph.client import get_neo4j_client

    client = get_neo4j_client()
    service = GraphService(client)

    # Query a process
    process = await service.get_process_by_id("boston_resident_parking_permit")

    # Get all steps for a process
    steps = await service.get_process_steps("boston_resident_parking_permit")

    # Get the process DAG for visualization
    dag = await service.get_process_dag("boston_resident_parking_permit")
    ```
"""

import logging
from datetime import date, datetime
from typing import Any

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.db.graph.client import Neo4jClient
from src.schemas.graph import (
    DocumentType,
    Office,
    Process,
    Requirement,
    RPPNeighborhood,
    Rule,
    Step,
)

logger = logging.getLogger(__name__)


class GraphServiceError(Exception):
    """Base exception for graph service errors."""

    pass


class NotFoundError(GraphServiceError):
    """Raised when a requested entity is not found."""

    pass


class ConnectionError(GraphServiceError):
    """Raised when there is a connection issue with Neo4j."""

    pass


class GraphService:
    """
    Service layer for querying the Neo4j government process graph.

    This class provides high-level query methods that return typed Pydantic models.
    It abstracts the complexity of Cypher queries and handles error cases.

    Attributes:
        client: Neo4jClient instance for database connections
    """

    def __init__(self, client: Neo4jClient) -> None:
        """
        Initialize the graph service.

        Args:
            client: Neo4jClient instance for database operations
        """
        self.client = client

    async def _execute_query(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dictionaries.

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            ConnectionError: If database connection fails
            GraphServiceError: For other database errors
        """
        try:
            async with self.client.get_session() as session:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
        except ServiceUnavailable as e:
            logger.error(f"Neo4j connection error: {e}")
            raise ConnectionError(f"Database connection failed: {e}") from e
        except Neo4jError as e:
            logger.error(f"Neo4j error executing query: {e}")
            raise GraphServiceError(f"Database error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            raise GraphServiceError(f"Unexpected error: {e}") from e

    def _node_to_dict(self, node: Any) -> dict[str, Any]:
        """
        Convert a Neo4j node to a dictionary.

        Args:
            node: Neo4j node object

        Returns:
            Dictionary representation of the node
        """
        if node is None:
            return {}
        return dict(node)

    def _convert_neo4j_types(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert Neo4j-specific types to Python types.

        Args:
            data: Dictionary with Neo4j types

        Returns:
            Dictionary with converted Python types
        """
        converted = {}
        for key, value in data.items():
            # Convert Neo4j Date to Python date
            if hasattr(value, "to_native"):
                converted[key] = value.to_native()
            # Convert Neo4j DateTime to Python datetime
            elif isinstance(value, datetime):
                converted[key] = value
            elif isinstance(value, date):
                converted[key] = value
            else:
                converted[key] = value
        return converted

    # ==================== Process Queries ====================

    async def get_process_by_id(self, process_id: str) -> Process | None:
        """
        Retrieve a process by its ID.

        Args:
            process_id: Unique process identifier (e.g., "boston_resident_parking_permit")

        Returns:
            Process model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {process_id: $process_id})
        RETURN p
        """

        records = await self._execute_query(query, {"process_id": process_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["p"])
        node_data = self._convert_neo4j_types(node_data)

        return Process(**node_data)

    async def get_all_processes(self) -> list[Process]:
        """
        Retrieve all processes in the database.

        Returns:
            List of Process models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process)
        RETURN p
        ORDER BY p.name
        """

        records = await self._execute_query(query)

        processes = []
        for record in records:
            node_data = self._node_to_dict(record["p"])
            node_data = self._convert_neo4j_types(node_data)
            processes.append(Process(**node_data))

        return processes

    async def get_processes_by_category(self, category: str) -> list[Process]:
        """
        Retrieve all processes in a specific category.

        Args:
            category: Process category (e.g., "permits", "licenses", "benefits")

        Returns:
            List of Process models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {category: $category})
        RETURN p
        ORDER BY p.name
        """

        records = await self._execute_query(query, {"category": category})

        processes = []
        for record in records:
            node_data = self._node_to_dict(record["p"])
            node_data = self._convert_neo4j_types(node_data)
            processes.append(Process(**node_data))

        return processes

    # ==================== Step Queries ====================

    async def get_step_by_id(self, step_id: str) -> Step | None:
        """
        Retrieve a step by its ID.

        Args:
            step_id: Unique step identifier (e.g., "rpp_step_1_check_eligibility")

        Returns:
            Step model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (s:Step {step_id: $step_id})
        RETURN s
        """

        records = await self._execute_query(query, {"step_id": step_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["s"])
        node_data = self._convert_neo4j_types(node_data)

        return Step(**node_data)

    async def get_process_steps(self, process_id: str) -> list[Step]:
        """
        Retrieve all steps for a given process, ordered by step order.

        Args:
            process_id: Process identifier

        Returns:
            List of Step models ordered by step.order

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {process_id: $process_id})-[:HAS_STEP]->(s:Step)
        RETURN s
        ORDER BY s.order ASC
        """

        records = await self._execute_query(query, {"process_id": process_id})

        steps = []
        for record in records:
            node_data = self._node_to_dict(record["s"])
            node_data = self._convert_neo4j_types(node_data)
            steps.append(Step(**node_data))

        return steps

    async def get_step_dependencies(self, step_id: str) -> list[Step]:
        """
        Retrieve all steps that the given step depends on.

        Args:
            step_id: Step identifier

        Returns:
            List of Step models that must be completed before this step

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (s:Step {step_id: $step_id})-[:DEPENDS_ON]->(dep:Step)
        RETURN dep
        ORDER BY dep.order ASC
        """

        records = await self._execute_query(query, {"step_id": step_id})

        dependencies = []
        for record in records:
            node_data = self._node_to_dict(record["dep"])
            node_data = self._convert_neo4j_types(node_data)
            dependencies.append(Step(**node_data))

        return dependencies

    # ==================== Requirement Queries ====================

    async def get_requirement_by_id(self, requirement_id: str) -> Requirement | None:
        """
        Retrieve a requirement by its ID.

        Args:
            requirement_id: Unique requirement identifier

        Returns:
            Requirement model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (r:Requirement {requirement_id: $requirement_id})
        RETURN r
        """

        records = await self._execute_query(query, {"requirement_id": requirement_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["r"])
        node_data = self._convert_neo4j_types(node_data)

        return Requirement(**node_data)

    async def get_process_requirements(self, process_id: str) -> list[Requirement]:
        """
        Retrieve all requirements for a given process.

        Args:
            process_id: Process identifier

        Returns:
            List of Requirement models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {process_id: $process_id})-[:REQUIRES]->(r:Requirement)
        RETURN r
        """

        records = await self._execute_query(query, {"process_id": process_id})

        requirements = []
        for record in records:
            node_data = self._node_to_dict(record["r"])
            node_data = self._convert_neo4j_types(node_data)
            requirements.append(Requirement(**node_data))

        return requirements

    async def get_hard_gate_requirements(self, process_id: str) -> list[Requirement]:
        """
        Retrieve all hard-gate requirements for a process (requirements that block progress).

        Args:
            process_id: Process identifier

        Returns:
            List of Requirement models that are hard gates

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {process_id: $process_id})-[:REQUIRES]->(r:Requirement)
        WHERE r.hard_gate = true
        RETURN r
        """

        records = await self._execute_query(query, {"process_id": process_id})

        requirements = []
        for record in records:
            node_data = self._node_to_dict(record["r"])
            node_data = self._convert_neo4j_types(node_data)
            requirements.append(Requirement(**node_data))

        return requirements

    # ==================== Document Type Queries ====================

    async def get_document_type_by_id(self, doc_type_id: str) -> DocumentType | None:
        """
        Retrieve a document type by its ID.

        Args:
            doc_type_id: Unique document type identifier

        Returns:
            DocumentType model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (dt:DocumentType {doc_type_id: $doc_type_id})
        RETURN dt
        """

        records = await self._execute_query(query, {"doc_type_id": doc_type_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["dt"])
        node_data = self._convert_neo4j_types(node_data)

        return DocumentType(**node_data)

    async def get_step_document_types(self, step_id: str) -> list[DocumentType]:
        """
        Retrieve all document types needed for a given step.

        Args:
            step_id: Step identifier

        Returns:
            List of DocumentType models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (s:Step {step_id: $step_id})-[:NEEDS_DOCUMENT]->(dt:DocumentType)
        RETURN dt
        """

        records = await self._execute_query(query, {"step_id": step_id})

        doc_types = []
        for record in records:
            node_data = self._node_to_dict(record["dt"])
            node_data = self._convert_neo4j_types(node_data)
            doc_types.append(DocumentType(**node_data))

        return doc_types

    async def get_requirement_document_types(self, requirement_id: str) -> list[DocumentType]:
        """
        Retrieve all document types that satisfy a given requirement.

        Args:
            requirement_id: Requirement identifier

        Returns:
            List of DocumentType models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (dt:DocumentType)-[:SATISFIES]->(r:Requirement {requirement_id: $requirement_id})
        RETURN dt
        """

        records = await self._execute_query(query, {"requirement_id": requirement_id})

        doc_types = []
        for record in records:
            node_data = self._node_to_dict(record["dt"])
            node_data = self._convert_neo4j_types(node_data)
            doc_types.append(DocumentType(**node_data))

        return doc_types

    # ==================== Office Queries ====================

    async def get_office_by_id(self, office_id: str) -> Office | None:
        """
        Retrieve an office by its ID.

        Args:
            office_id: Unique office identifier

        Returns:
            Office model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (o:Office {office_id: $office_id})
        RETURN o
        """

        records = await self._execute_query(query, {"office_id": office_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["o"])
        node_data = self._convert_neo4j_types(node_data)

        return Office(**node_data)

    async def get_step_office(self, step_id: str) -> Office | None:
        """
        Retrieve the office where a step is handled.

        Args:
            step_id: Step identifier

        Returns:
            Office model or None if step has no associated office

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (s:Step {step_id: $step_id})-[:HANDLED_AT]->(o:Office)
        RETURN o
        """

        records = await self._execute_query(query, {"step_id": step_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["o"])
        node_data = self._convert_neo4j_types(node_data)

        return Office(**node_data)

    # ==================== Rule Queries ====================

    async def get_rule_by_id(self, rule_id: str) -> Rule | None:
        """
        Retrieve a rule by its ID.

        Args:
            rule_id: Unique rule identifier

        Returns:
            Rule model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (r:Rule {rule_id: $rule_id})
        RETURN r
        """

        records = await self._execute_query(query, {"rule_id": rule_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["r"])
        node_data = self._convert_neo4j_types(node_data)

        return Rule(**node_data)

    async def get_requirement_rules(self, requirement_id: str) -> list[Rule]:
        """
        Retrieve all rules that govern a given requirement.

        Args:
            requirement_id: Requirement identifier

        Returns:
            List of Rule models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (r:Rule)-[:RULE_GOVERNS]->(req:Requirement {requirement_id: $requirement_id})
        RETURN r
        """

        records = await self._execute_query(query, {"requirement_id": requirement_id})

        rules = []
        for record in records:
            node_data = self._node_to_dict(record["r"])
            node_data = self._convert_neo4j_types(node_data)
            rules.append(Rule(**node_data))

        return rules

    # ==================== RPP Neighborhood Queries ====================

    async def get_rpp_neighborhood_by_id(self, nbrhd_id: str) -> RPPNeighborhood | None:
        """
        Retrieve an RPP neighborhood by its ID.

        Args:
            nbrhd_id: Unique neighborhood identifier

        Returns:
            RPPNeighborhood model or None if not found

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (n:RPPNeighborhood {nbrhd_id: $nbrhd_id})
        RETURN n
        """

        records = await self._execute_query(query, {"nbrhd_id": nbrhd_id})

        if not records:
            return None

        node_data = self._node_to_dict(records[0]["n"])
        node_data = self._convert_neo4j_types(node_data)

        return RPPNeighborhood(**node_data)

    async def get_process_neighborhoods(self, process_id: str) -> list[RPPNeighborhood]:
        """
        Retrieve all neighborhoods where a process applies.

        Args:
            process_id: Process identifier

        Returns:
            List of RPPNeighborhood models

        Raises:
            GraphServiceError: If query execution fails
        """
        query = """
        MATCH (p:Process {process_id: $process_id})-[:APPLIES_IN]->(n:RPPNeighborhood)
        RETURN n
        ORDER BY n.name
        """

        records = await self._execute_query(query, {"process_id": process_id})

        neighborhoods = []
        for record in records:
            node_data = self._node_to_dict(record["n"])
            node_data = self._convert_neo4j_types(node_data)
            neighborhoods.append(RPPNeighborhood(**node_data))

        return neighborhoods

    # ==================== DAG/Visualization Queries ====================

    async def get_process_dag(self, process_id: str) -> dict[str, Any]:
        """
        Retrieve the complete process DAG for visualization.

        This returns nodes (steps) and edges (dependencies) suitable for rendering
        in a frontend visualization library like D3.js or Cytoscape.js.

        Args:
            process_id: Process identifier

        Returns:
            Dictionary with 'nodes' and 'edges' lists:
            {
                "nodes": [{"id": "step_id", "label": "step name", "data": {...}}, ...],
                "edges": [{"source": "step_1", "target": "step_2", "type": "DEPENDS_ON"}, ...]
            }

        Raises:
            GraphServiceError: If query execution fails
        """
        # Get all steps
        steps = await self.get_process_steps(process_id)

        nodes = []
        for step in steps:
            nodes.append(
                {
                    "id": step.step_id,
                    "label": step.name,
                    "order": step.order,
                    "data": step.model_dump(),
                }
            )

        # Get all dependencies
        edges_query = """
        MATCH (p:Process {process_id: $process_id})-[:HAS_STEP]->(s1:Step)
        MATCH (s1)-[r:DEPENDS_ON]->(s2:Step)
        RETURN s1.step_id as source, s2.step_id as target, type(r) as rel_type
        """

        records = await self._execute_query(edges_query, {"process_id": process_id})

        edges = []
        for record in records:
            edges.append(
                {
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["rel_type"],
                }
            )

        return {"nodes": nodes, "edges": edges}

    # ==================== Health Check ====================

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the graph service.

        Returns:
            Dictionary with health status information

        Raises:
            GraphServiceError: If health check fails
        """
        try:
            # Use the client's built-in health check
            health = await self.client.health_check()
            return health
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "details": "Service error",
                "error": str(e),
            }


def get_graph_service(client: Neo4jClient | None = None) -> GraphService:
    """
    Factory function to create a GraphService instance.

    This is useful for dependency injection in FastAPI routes.

    Args:
        client: Optional Neo4jClient instance. If None, creates a new one.

    Returns:
        GraphService instance

    Example:
        ```python
        from fastapi import Depends
        from src.services.graph_service import get_graph_service, GraphService

        @app.get("/processes/{process_id}")
        async def get_process(
            process_id: str,
            service: GraphService = Depends(get_graph_service)
        ):
            process = await service.get_process_by_id(process_id)
            return process
        ```
    """
    if client is None:
        from src.db.graph.client import get_neo4j_client

        client = get_neo4j_client()

    return GraphService(client)
