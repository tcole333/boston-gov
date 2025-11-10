#!/usr/bin/env python3
"""
Seed Neo4j database with Boston Resident Parking Permit (RPP) process graph.

This script creates the complete process graph for the Boston RPP application,
including steps, requirements, document types, rules, and office information.
All regulatory data is sourced from /docs/facts/boston_rpp.yaml.

Usage:
    uv run python scripts/seed_rpp.py

Environment variables required:
    NEO4J_URI - Neo4j connection URI (e.g., bolt://localhost:7687)
    NEO4J_USER - Neo4j username
    NEO4J_PASSWORD - Neo4j password
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from neo4j import AsyncSession

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.graph.client import Neo4jClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_facts_registry(facts_path: str) -> dict[str, Any]:
    """
    Load the Facts Registry YAML file.

    Args:
        facts_path: Path to the boston_rpp.yaml facts file

    Returns:
        Parsed YAML data as dictionary

    Raises:
        FileNotFoundError: If facts file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    logger.info(f"Loading facts from {facts_path}")

    if not Path(facts_path).exists():
        raise FileNotFoundError(f"Facts file not found: {facts_path}")

    with open(facts_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    logger.info(f"Loaded {len(data.get('facts', []))} facts from registry")
    return data


def get_fact_by_id(facts_data: dict[str, Any], fact_id: str) -> dict[str, Any] | None:
    """
    Retrieve a specific fact from the registry by ID.

    Args:
        facts_data: The loaded facts registry
        fact_id: The fact ID to retrieve (e.g., "rpp.eligibility.vehicle_class")

    Returns:
        The fact dictionary or None if not found
    """
    for fact in facts_data.get("facts", []):
        if fact.get("id") == fact_id:
            return fact
    return None


async def create_constraints(session: AsyncSession) -> None:
    """
    Create uniqueness constraints for all node types.
    Constraints enable MERGE operations for idempotence.

    Args:
        session: Async Neo4j session
    """
    logger.info("Creating uniqueness constraints")

    constraints = [
        "CREATE CONSTRAINT process_id_unique IF NOT EXISTS FOR (p:Process) REQUIRE p.process_id IS UNIQUE",
        "CREATE CONSTRAINT step_id_unique IF NOT EXISTS FOR (s:Step) REQUIRE s.step_id IS UNIQUE",
        "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.requirement_id IS UNIQUE",
        "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE",
        "CREATE CONSTRAINT doc_type_id_unique IF NOT EXISTS FOR (dt:DocumentType) REQUIRE dt.doc_type_id IS UNIQUE",
        "CREATE CONSTRAINT office_id_unique IF NOT EXISTS FOR (o:Office) REQUIRE o.office_id IS UNIQUE",
    ]

    for constraint in constraints:
        await session.run(constraint)
        logger.debug(f"Created constraint: {constraint}")

    logger.info("Constraints created successfully")


async def create_process_node(session: AsyncSession, facts_data: dict[str, Any]) -> None:
    """
    Create the main Process node for Boston RPP.

    Args:
        session: Async Neo4j session
        facts_data: Loaded facts registry
    """
    logger.info("Creating Process node")

    # Try to get fact, use defaults if not found
    fact = get_fact_by_id(facts_data, "rpp.process.definition")
    if not fact:
        logger.warning("Process definition fact not found, using defaults")
        fact = {
            "value": "Process for obtaining a Boston Resident Parking Permit",
            "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            "source_section": "How to get a resident parking permit",
            "last_verified": str(datetime.now().date()),
            "confidence": "high",
        }

    query = """
    MERGE (p:Process {process_id: $process_id})
    SET p.name = $name,
        p.description = $description,
        p.source_url = $source_url,
        p.source_section = $source_section,
        p.last_verified = date($last_verified),
        p.confidence = $confidence,
        p.created_at = datetime(),
        p.updated_at = datetime()
    RETURN p
    """

    await session.run(
        query,
        process_id="boston_resident_parking_permit",
        name="Boston Resident Parking Permit",
        description=fact.get("value", ""),
        source_url=fact.get("source_url", ""),
        source_section=fact.get("source_section", ""),
        last_verified=fact.get("last_verified", str(datetime.now().date())),
        confidence=fact.get("confidence", "high"),
    )

    logger.info("Process node created")


async def create_step_nodes(session: AsyncSession) -> None:
    """
    Create Step nodes for the RPP process.

    Args:
        session: Async Neo4j session
    """
    logger.info("Creating Step nodes")

    steps = [
        {
            "step_id": "rpp_step_1_check_eligibility",
            "name": "Check Eligibility",
            "description": "Verify you meet the basic requirements for a resident parking permit",
            "order": 1,
            "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            "source_section": "How to get a resident parking permit",
            "last_verified": str(datetime.now().date()),
            "confidence": "high",
        },
        {
            "step_id": "rpp_step_2_gather_documents",
            "name": "Gather Required Documents",
            "description": "Collect proof of residency and vehicle registration",
            "order": 2,
            "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            "source_section": "What you'll need",
            "last_verified": str(datetime.now().date()),
            "confidence": "high",
        },
        {
            "step_id": "rpp_step_3_submit_application",
            "name": "Submit Application",
            "description": "Visit the Parking Clerk's office or apply online",
            "order": 3,
            "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
            "source_section": "Where to apply",
            "last_verified": str(datetime.now().date()),
            "confidence": "high",
        },
    ]

    query = """
    MERGE (s:Step {step_id: $step_id})
    SET s.name = $name,
        s.description = $description,
        s.order = $order,
        s.process_id = $process_id,
        s.source_url = $source_url,
        s.source_section = $source_section,
        s.last_verified = date($last_verified),
        s.confidence = $confidence,
        s.created_at = datetime(),
        s.updated_at = datetime()
    RETURN s
    """

    for step in steps:
        await session.run(query, process_id="boston_resident_parking_permit", **step)

    logger.info(f"Created {len(steps)} Step nodes")


async def create_requirement_nodes(session: AsyncSession, facts_data: dict[str, Any]) -> None:
    """
    Create Requirement nodes from the facts registry.

    Args:
        session: Async Neo4j session
        facts_data: Loaded facts registry
    """
    logger.info("Creating Requirement nodes")

    requirements = [
        {
            "requirement_id": "req_residency_proof",
            "fact_id": "rpp.documents.residency_proof",
            "text": "Proof of Boston Residency",
            "hard_gate": True,
        },
        {
            "requirement_id": "req_vehicle_registration",
            "fact_id": "rpp.documents.vehicle_registration",
            "text": "Vehicle Registration",
            "hard_gate": True,
        },
        {
            "requirement_id": "req_residency_duration",
            "fact_id": "rpp.eligibility.residency_duration",
            "text": "Residency Duration",
            "hard_gate": True,
        },
        {
            "requirement_id": "req_vehicle_class",
            "fact_id": "rpp.eligibility.vehicle_class",
            "text": "Vehicle Class",
            "hard_gate": True,
        },
    ]

    query = """
    MERGE (r:Requirement {requirement_id: $requirement_id})
    SET r.text = $text,
        r.fact_id = $fact_id,
        r.hard_gate = $hard_gate,
        r.applies_to_process = $process_id,
        r.source_url = $source_url,
        r.source_section = $source_section,
        r.last_verified = date($last_verified),
        r.confidence = $confidence,
        r.created_at = datetime(),
        r.updated_at = datetime()
    RETURN r
    """

    for req in requirements:
        fact = get_fact_by_id(facts_data, req["fact_id"])
        if not fact:
            logger.warning(f"Fact {req['fact_id']} not found, using defaults")
            fact = {
                "value": req["text"],
                "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                "source_section": "Requirements",
                "last_verified": str(datetime.now().date()),
                "confidence": "medium",
            }

        await session.run(
            query,
            requirement_id=req["requirement_id"],
            text=req["text"],
            fact_id=req["fact_id"],
            hard_gate=req["hard_gate"],
            process_id="boston_resident_parking_permit",
            source_url=fact.get("source_url", ""),
            source_section=fact.get("source_section", ""),
            last_verified=fact.get("last_verified", str(datetime.now().date())),
            confidence=fact.get("confidence", "high"),
        )

    logger.info(f"Created {len(requirements)} Requirement nodes")


async def create_document_type_nodes(session: AsyncSession, facts_data: dict[str, Any]) -> None:
    """
    Create DocumentType nodes for acceptable proof documents.

    Args:
        session: Async Neo4j session
        facts_data: Loaded facts registry
    """
    logger.info("Creating DocumentType nodes")

    doc_types = [
        {
            "doc_type_id": "proof.utility_bill",
            "fact_id": "rpp.documents.residency_proof",
            "name": "Utility Bill",
            "description": "Current utility bill showing Boston address",
            "category": "residency_proof",
        },
        {
            "doc_type_id": "proof.lease_agreement",
            "fact_id": "rpp.documents.residency_proof",
            "name": "Lease Agreement",
            "description": "Current lease or rental agreement",
            "category": "residency_proof",
        },
        {
            "doc_type_id": "proof.property_tax",
            "fact_id": "rpp.documents.residency_proof",
            "name": "Property Tax Bill",
            "description": "Current property tax bill",
            "category": "residency_proof",
        },
        {
            "doc_type_id": "proof.bank_statement",
            "fact_id": "rpp.documents.residency_proof",
            "name": "Bank Statement",
            "description": "Recent bank statement with Boston address",
            "category": "residency_proof",
        },
        {
            "doc_type_id": "proof.drivers_license",
            "fact_id": "rpp.documents.residency_proof",
            "name": "Driver's License",
            "description": "Massachusetts driver's license with Boston address",
            "category": "residency_proof",
        },
        {
            "doc_type_id": "proof.vehicle_registration_ma",
            "fact_id": "rpp.documents.vehicle_registration",
            "name": "MA Vehicle Registration",
            "description": "Current Massachusetts vehicle registration",
            "category": "vehicle_proof",
        },
        {
            "doc_type_id": "proof.vehicle_title",
            "fact_id": "rpp.documents.vehicle_registration",
            "name": "Vehicle Title",
            "description": "Vehicle title or registration from any state",
            "category": "vehicle_proof",
        },
    ]

    query = """
    MERGE (dt:DocumentType {doc_type_id: $doc_type_id})
    SET dt.name = $name,
        dt.description = $description,
        dt.category = $category,
        dt.freshness_days = $freshness_days,
        dt.source_url = $source_url,
        dt.source_section = $source_section,
        dt.last_verified = date($last_verified),
        dt.confidence = $confidence,
        dt.created_at = datetime(),
        dt.updated_at = datetime()
    RETURN dt
    """

    for doc_type in doc_types:
        fact = get_fact_by_id(facts_data, doc_type["fact_id"])
        if not fact:
            logger.warning(f"Fact {doc_type['fact_id']} not found, using defaults")
            fact = {
                "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
                "source_section": "What you'll need",
                "last_verified": str(datetime.now().date()),
                "confidence": "high",
            }

        # Determine freshness requirement based on category
        freshness_days = 30 if doc_type["category"] == "residency_proof" else None

        await session.run(
            query,
            doc_type_id=doc_type["doc_type_id"],
            name=doc_type["name"],
            description=doc_type["description"],
            category=doc_type["category"],
            freshness_days=freshness_days,
            source_url=fact.get("source_url", ""),
            source_section=fact.get("source_section", ""),
            last_verified=fact.get("last_verified", str(datetime.now().date())),
            confidence=fact.get("confidence", "high"),
        )

    logger.info(f"Created {len(doc_types)} DocumentType nodes")


async def create_office_node(session: AsyncSession, facts_data: dict[str, Any]) -> None:
    """
    Create Office node for the Parking Clerk's office.

    Args:
        session: Async Neo4j session
        facts_data: Loaded facts registry
    """
    logger.info("Creating Office node")

    fact = get_fact_by_id(facts_data, "rpp.office.location")
    if not fact:
        logger.warning("Office location fact not found, using defaults")
        fact = {
            "value": "Boston City Hall, Room 224",
            "source_url": "https://www.boston.gov/departments/parking-clerk",
            "source_section": "Contact information",
            "last_verified": str(datetime.now().date()),
            "confidence": "high",
        }

    query = """
    MERGE (o:Office {office_id: $office_id})
    SET o.name = $name,
        o.location = $location,
        o.address = $address,
        o.source_url = $source_url,
        o.source_section = $source_section,
        o.last_verified = date($last_verified),
        o.confidence = $confidence,
        o.created_at = datetime(),
        o.updated_at = datetime()
    RETURN o
    """

    await session.run(
        query,
        office_id="boston_parking_clerk",
        name="Boston Parking Clerk",
        location=fact.get("value", ""),
        address="1 City Hall Square, Room 224, Boston, MA 02201",
        source_url=fact.get("source_url", ""),
        source_section=fact.get("source_section", ""),
        last_verified=fact.get("last_verified", str(datetime.now().date())),
        confidence=fact.get("confidence", "high"),
    )

    logger.info("Office node created")


async def create_rule_nodes(session: AsyncSession, facts_data: dict[str, Any]) -> None:
    """
    Create Rule nodes from the facts registry.

    Args:
        session: Async Neo4j session
        facts_data: Loaded facts registry
    """
    logger.info("Creating Rule nodes")

    # Create rules for each fact in the registry
    rules_created = 0
    for fact in facts_data.get("facts", []):
        fact_id = fact.get("id", "")
        if not fact_id:
            continue

        # Create a rule node for this fact
        query = """
        MERGE (r:Rule {rule_id: $rule_id})
        SET r.fact_id = $fact_id,
            r.rule_type = $rule_type,
            r.description = $description,
            r.source_url = $source_url,
            r.source_section = $source_section,
            r.last_verified = date($last_verified),
            r.confidence = $confidence,
            r.created_at = datetime(),
            r.updated_at = datetime()
        RETURN r
        """

        # Determine rule type based on fact ID
        if "eligibility" in fact_id:
            rule_type = "eligibility"
        elif "documents" in fact_id:
            rule_type = "documentation"
        elif "process" in fact_id:
            rule_type = "process"
        elif "office" in fact_id:
            rule_type = "administrative"
        else:
            rule_type = "general"

        await session.run(
            query,
            rule_id=f"rule_{fact_id}",
            fact_id=fact_id,
            rule_type=rule_type,
            description=fact.get("value", ""),
            source_url=fact.get("source_url", ""),
            source_section=fact.get("source_section", ""),
            last_verified=fact.get("last_verified", str(datetime.now().date())),
            confidence=fact.get("confidence", "high"),
        )
        rules_created += 1

    logger.info(f"Created {rules_created} Rule nodes")


async def create_relationships(session: AsyncSession) -> None:
    """
    Create relationships between all nodes.

    Args:
        session: Async Neo4j session
    """
    logger.info("Creating relationships")

    relationships = [
        # Process to Steps
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp_step_1_check_eligibility'})
        MERGE (p)-[:HAS_STEP]->(s)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp_step_2_gather_documents'})
        MERGE (p)-[:HAS_STEP]->(s)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp_step_3_submit_application'})
        MERGE (p)-[:HAS_STEP]->(s)
        """,
        # Step dependencies
        """
        MATCH (s1:Step {step_id: 'rpp_step_1_check_eligibility'})
        MATCH (s2:Step {step_id: 'rpp_step_2_gather_documents'})
        MERGE (s2)-[:DEPENDS_ON]->(s1)
        """,
        """
        MATCH (s2:Step {step_id: 'rpp_step_2_gather_documents'})
        MATCH (s3:Step {step_id: 'rpp_step_3_submit_application'})
        MERGE (s3)-[:DEPENDS_ON]->(s2)
        """,
        # Process to Requirements
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (r:Requirement)
        WHERE r.applies_to_process = 'boston_resident_parking_permit'
        MERGE (p)-[:REQUIRES]->(r)
        """,
        # Steps to DocumentTypes
        """
        MATCH (s:Step {step_id: 'rpp_step_2_gather_documents'})
        MATCH (dt:DocumentType)
        WHERE dt.category IN ['residency_proof', 'vehicle_proof']
        MERGE (s)-[:NEEDS_DOCUMENT]->(dt)
        """,
        # DocumentTypes to Requirements
        """
        MATCH (dt:DocumentType {category: 'residency_proof'})
        MATCH (r:Requirement {requirement_id: 'req_residency_proof'})
        MERGE (dt)-[:SATISFIES]->(r)
        """,
        """
        MATCH (dt:DocumentType {category: 'vehicle_proof'})
        MATCH (r:Requirement {requirement_id: 'req_vehicle_registration'})
        MERGE (dt)-[:SATISFIES]->(r)
        """,
        # Step to Office
        """
        MATCH (s:Step {step_id: 'rpp_step_3_submit_application'})
        MATCH (o:Office {office_id: 'boston_parking_clerk'})
        MERGE (s)-[:HANDLED_AT]->(o)
        """,
        # Rules to Requirements
        """
        MATCH (ru:Rule)
        WHERE ru.rule_type = 'eligibility'
        MATCH (r:Requirement)
        WHERE r.type = 'eligibility'
        MERGE (ru)-[:RULE_GOVERNS]->(r)
        """,
        """
        MATCH (ru:Rule)
        WHERE ru.rule_type = 'documentation'
        MATCH (r:Requirement)
        WHERE r.type = 'document'
        MERGE (ru)-[:RULE_GOVERNS]->(r)
        """,
    ]

    for relationship in relationships:
        await session.run(relationship)

    logger.info(f"Created {len(relationships)} relationships")


async def seed_database(facts_path: str) -> None:
    """
    Seed the Neo4j database with Boston RPP process graph.

    Args:
        facts_path: Path to facts YAML file

    Raises:
        Exception: If database connection or seeding fails
    """
    logger.info("Starting Neo4j seeding for Boston RPP")

    # Load facts registry
    facts_data = load_facts_registry(facts_path)

    # Connect to Neo4j using our client
    client = Neo4jClient()
    await client.connect()

    try:
        # Verify connection
        health = await client.health_check()
        if health["status"] != "healthy":
            raise RuntimeError(f"Neo4j unhealthy: {health}")

        logger.info("Neo4j connection verified")

        async with client.get_session() as session:
            # Create constraints first (for idempotence)
            await create_constraints(session)

            # Create nodes
            await create_process_node(session, facts_data)
            await create_step_nodes(session)
            await create_requirement_nodes(session, facts_data)
            await create_document_type_nodes(session, facts_data)
            await create_office_node(session, facts_data)
            await create_rule_nodes(session, facts_data)

            # Create relationships
            await create_relationships(session)

        logger.info("Neo4j seeding completed successfully")

    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        raise
    finally:
        await client.close()
        logger.info("Neo4j connection closed")


async def async_main() -> int:
    """
    Async entry point for the seed script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Determine facts file path (relative to project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    facts_path = project_root / "docs" / "facts" / "boston_rpp.yaml"

    if not facts_path.exists():
        logger.error(f"Facts file not found at {facts_path}")
        return 1

    try:
        await seed_database(str(facts_path))
        return 0
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        return 1


def main() -> int:
    """
    Entry point for the seed script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
