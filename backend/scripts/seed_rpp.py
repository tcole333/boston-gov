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

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from neo4j import GraphDatabase, Session

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

    with open(facts_path, "r", encoding="utf-8") as f:
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


def create_constraints(session: Session) -> None:
    """
    Create uniqueness constraints for all node types.
    Constraints enable MERGE operations for idempotence.

    Args:
        session: Neo4j session
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
        session.run(constraint)
        logger.debug(f"Created constraint: {constraint}")

    logger.info(f"Created {len(constraints)} constraints")


def create_process_node(session: Session, facts_data: dict[str, Any]) -> None:
    """
    Create the main Process node for Boston RPP.

    Args:
        session: Neo4j session
        facts_data: Facts registry data
    """
    logger.info("Creating Process node")

    # Use the main how-to page as the primary source
    source_url = "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"

    query = """
    MERGE (p:Process {process_id: $process_id})
    ON CREATE SET
        p.created_at = datetime(),
        p.name = $name,
        p.description = $description,
        p.category = $category,
        p.jurisdiction = $jurisdiction,
        p.source_url = $source_url,
        p.last_verified = date($last_verified),
        p.confidence = $confidence
    ON MATCH SET
        p.name = $name,
        p.description = $description,
        p.category = $category,
        p.jurisdiction = $jurisdiction,
        p.source_url = $source_url,
        p.last_verified = date($last_verified),
        p.confidence = $confidence,
        p.updated_at = datetime()
    RETURN p
    """

    params = {
        "process_id": "boston_resident_parking_permit",
        "name": "Boston Resident Parking Permit",
        "description": "Obtain a neighborhood-specific parking permit for your MA-registered vehicle at your Boston residence",
        "category": "permits",
        "jurisdiction": "City of Boston",
        "source_url": source_url,
        "last_verified": "2025-11-09",
        "confidence": "high",
    }

    session.run(query, params)
    logger.info("Process node created")


def create_step_nodes(session: Session) -> None:
    """
    Create the three main Step nodes for the RPP process.

    Args:
        session: Neo4j session
    """
    logger.info("Creating Step nodes")

    source_url = "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"

    steps = [
        {
            "step_id": "rpp.check_eligibility",
            "process_id": "boston_resident_parking_permit",
            "name": "Check Eligibility",
            "description": "Verify vehicle class, MA registration at Boston address, and no unpaid tickets",
            "order": 1,
            "estimated_time_minutes": 5,
            "cost_usd": 0.0,
            "optional": False,
        },
        {
            "step_id": "rpp.gather_documents",
            "process_id": "boston_resident_parking_permit",
            "name": "Gather Documents",
            "description": "Obtain one proof of residency dated within 30 days with name matching registration",
            "order": 2,
            "estimated_time_minutes": 15,
            "cost_usd": 0.0,
            "optional": False,
        },
        {
            "step_id": "rpp.submit_application",
            "process_id": "boston_resident_parking_permit",
            "name": "Submit Application",
            "description": "Apply online or in person at City Hall Room 224",
            "order": 3,
            "estimated_time_minutes": 20,
            "cost_usd": 0.0,
            "optional": False,
        },
    ]

    query = """
    MERGE (s:Step {step_id: $step_id})
    ON CREATE SET
        s.created_at = datetime(),
        s.process_id = $process_id,
        s.name = $name,
        s.description = $description,
        s.order = $order,
        s.estimated_time_minutes = $estimated_time_minutes,
        s.cost_usd = $cost_usd,
        s.optional = $optional,
        s.source_url = $source_url,
        s.last_verified = date($last_verified),
        s.confidence = $confidence
    ON MATCH SET
        s.process_id = $process_id,
        s.name = $name,
        s.description = $description,
        s.order = $order,
        s.estimated_time_minutes = $estimated_time_minutes,
        s.cost_usd = $cost_usd,
        s.optional = $optional,
        s.source_url = $source_url,
        s.last_verified = date($last_verified),
        s.confidence = $confidence,
        s.updated_at = datetime()
    RETURN s
    """

    for step in steps:
        params = {
            **step,
            "source_url": source_url,
            "last_verified": "2025-11-09",
            "confidence": "high",
        }
        session.run(query, params)
        logger.debug(f"Created step: {step['step_id']}")

    logger.info(f"Created {len(steps)} Step nodes")


def create_requirement_nodes(session: Session, facts_data: dict[str, Any]) -> None:
    """
    Create Requirement nodes for eligibility conditions.

    Args:
        session: Neo4j session
        facts_data: Facts registry data
    """
    logger.info("Creating Requirement nodes")

    requirements = [
        {
            "requirement_id": "rpp.req.vehicle_class",
            "fact_id": "rpp.eligibility.vehicle_class",
            "hard_gate": True,
        },
        {
            "requirement_id": "rpp.req.ma_registration",
            "fact_id": "rpp.eligibility.registration_state",
            "hard_gate": True,
        },
        {
            "requirement_id": "rpp.req.no_unpaid_tickets",
            "fact_id": "rpp.eligibility.no_unpaid_tickets",
            "hard_gate": True,
        },
        {
            "requirement_id": "rpp.req.proof_of_residency",
            "fact_id": "rpp.proof_of_residency.count",
            "hard_gate": True,
        },
    ]

    query = """
    MERGE (r:Requirement {requirement_id: $requirement_id})
    ON CREATE SET
        r.created_at = datetime(),
        r.text = $text,
        r.fact_id = $fact_id,
        r.applies_to_process = $applies_to_process,
        r.hard_gate = $hard_gate,
        r.source_url = $source_url,
        r.source_section = $source_section,
        r.last_verified = date($last_verified),
        r.confidence = $confidence
    ON MATCH SET
        r.text = $text,
        r.fact_id = $fact_id,
        r.applies_to_process = $applies_to_process,
        r.hard_gate = $hard_gate,
        r.source_url = $source_url,
        r.source_section = $source_section,
        r.last_verified = date($last_verified),
        r.confidence = $confidence,
        r.updated_at = datetime()
    RETURN r
    """

    for req in requirements:
        fact = get_fact_by_id(facts_data, req["fact_id"])
        if not fact:
            logger.warning(f"Fact {req['fact_id']} not found in registry")
            continue

        params = {
            "requirement_id": req["requirement_id"],
            "text": fact["text"],
            "fact_id": req["fact_id"],
            "applies_to_process": "boston_resident_parking_permit",
            "hard_gate": req["hard_gate"],
            "source_url": fact["source_url"],
            "source_section": fact.get("source_section", ""),
            "last_verified": fact["last_verified"],
            "confidence": fact["confidence"],
        }
        session.run(query, params)
        logger.debug(f"Created requirement: {req['requirement_id']}")

    logger.info(f"Created {len(requirements)} Requirement nodes")


def create_document_type_nodes(session: Session, facts_data: dict[str, Any]) -> None:
    """
    Create DocumentType nodes for proof of residency documents.

    Args:
        session: Neo4j session
        facts_data: Facts registry data
    """
    logger.info("Creating DocumentType nodes")

    # Get the accepted types fact
    accepted_types_fact = get_fact_by_id(facts_data, "rpp.proof_of_residency.accepted_types")
    recency_fact = get_fact_by_id(facts_data, "rpp.proof_of_residency.recency")
    name_match_fact = get_fact_by_id(facts_data, "rpp.proof_of_residency.name_match")

    if not accepted_types_fact or not recency_fact or not name_match_fact:
        logger.error("Required proof of residency facts not found")
        return

    # Define the 7 document types mentioned in accepted_types fact
    doc_types = [
        {
            "doc_type_id": "proof.utility_bill",
            "name": "Utility bill (gas/electric/telephone)",
            "examples": ["National Grid", "Eversource", "Verizon"],
        },
        {
            "doc_type_id": "proof.cable_bill",
            "name": "Cable bill",
            "examples": ["Comcast", "RCN", "Verizon Fios"],
        },
        {
            "doc_type_id": "proof.bank_statement",
            "name": "Bank statement",
            "examples": ["Bank of America", "Citizens Bank", "TD Bank"],
        },
        {
            "doc_type_id": "proof.mortgage_statement",
            "name": "Mortgage statement",
            "examples": ["Mortgage servicer statement"],
        },
        {
            "doc_type_id": "proof.credit_card_statement",
            "name": "Credit card statement",
            "examples": ["Credit card billing statement"],
        },
        {
            "doc_type_id": "proof.water_sewer_bill",
            "name": "Water/sewer bill",
            "examples": ["BWSC bill"],
        },
        {
            "doc_type_id": "proof.lease_agreement",
            "name": "Lease agreement",
            "examples": ["Signed residential lease"],
        },
    ]

    query = """
    MERGE (dt:DocumentType {doc_type_id: $doc_type_id})
    ON CREATE SET
        dt.created_at = datetime(),
        dt.name = $name,
        dt.freshness_days = $freshness_days,
        dt.name_match_required = $name_match_required,
        dt.address_match_required = $address_match_required,
        dt.examples = $examples,
        dt.source_url = $source_url,
        dt.last_verified = date($last_verified),
        dt.confidence = $confidence
    ON MATCH SET
        dt.name = $name,
        dt.freshness_days = $freshness_days,
        dt.name_match_required = $name_match_required,
        dt.address_match_required = $address_match_required,
        dt.examples = $examples,
        dt.source_url = $source_url,
        dt.last_verified = date($last_verified),
        dt.confidence = $confidence,
        dt.updated_at = datetime()
    RETURN dt
    """

    for doc_type in doc_types:
        params = {
            "doc_type_id": doc_type["doc_type_id"],
            "name": doc_type["name"],
            "freshness_days": 30,  # From recency fact
            "name_match_required": True,  # From name_match fact
            "address_match_required": True,  # Implied by registration address matching
            "examples": doc_type["examples"],
            "source_url": accepted_types_fact["source_url"],
            "last_verified": accepted_types_fact["last_verified"],
            "confidence": accepted_types_fact["confidence"],
        }
        session.run(query, params)
        logger.debug(f"Created document type: {doc_type['doc_type_id']}")

    logger.info(f"Created {len(doc_types)} DocumentType nodes")


def create_office_node(session: Session, facts_data: dict[str, Any]) -> None:
    """
    Create the Office node for the Parking Clerk office.

    Args:
        session: Neo4j session
        facts_data: Facts registry data
    """
    logger.info("Creating Office node")

    location_fact = get_fact_by_id(facts_data, "rpp.office.location")
    hours_fact = get_fact_by_id(facts_data, "rpp.office.hours")
    phone_fact = get_fact_by_id(facts_data, "rpp.office.phone")
    email_fact = get_fact_by_id(facts_data, "rpp.office.email")

    if not all([location_fact, hours_fact, phone_fact, email_fact]):
        logger.error("Required office facts not found")
        return

    query = """
    MERGE (o:Office {office_id: $office_id})
    ON CREATE SET
        o.created_at = datetime(),
        o.name = $name,
        o.address = $address,
        o.room = $room,
        o.hours = $hours,
        o.phone = $phone,
        o.email = $email,
        o.source_url = $source_url,
        o.last_verified = date($last_verified),
        o.confidence = $confidence
    ON MATCH SET
        o.name = $name,
        o.address = $address,
        o.room = $room,
        o.hours = $hours,
        o.phone = $phone,
        o.email = $email,
        o.source_url = $source_url,
        o.last_verified = date($last_verified),
        o.confidence = $confidence,
        o.updated_at = datetime()
    RETURN o
    """

    params = {
        "office_id": "parking_clerk",
        "name": "Office of the Parking Clerk",
        "address": "1 City Hall Square, Boston MA 02201",
        "room": "224",
        "hours": "Monday-Friday, 9:00 AM - 4:30 PM",
        "phone": "617-635-4410",
        "email": "parking@boston.gov",
        "source_url": location_fact["source_url"],
        "last_verified": location_fact["last_verified"],
        "confidence": location_fact["confidence"],
    }

    session.run(query, params)
    logger.info("Office node created")


def create_rule_nodes(session: Session, facts_data: dict[str, Any]) -> None:
    """
    Create Rule nodes for all facts in the registry.

    Args:
        session: Neo4j session
        facts_data: Facts registry data
    """
    logger.info("Creating Rule nodes")

    query = """
    MERGE (r:Rule {rule_id: $rule_id})
    ON CREATE SET
        r.created_at = datetime(),
        r.text = $text,
        r.fact_id = $fact_id,
        r.scope = $scope,
        r.source_url = $source_url,
        r.source_section = $source_section,
        r.last_verified = date($last_verified),
        r.confidence = $confidence,
        r.note = $note
    ON MATCH SET
        r.text = $text,
        r.fact_id = $fact_id,
        r.scope = $scope,
        r.source_url = $source_url,
        r.source_section = $source_section,
        r.last_verified = date($last_verified),
        r.confidence = $confidence,
        r.note = $note,
        r.updated_at = datetime()
    RETURN r
    """

    facts = facts_data.get("facts", [])
    created_count = 0

    for fact in facts:
        # Determine scope from fact ID
        fact_id = fact.get("id", "")
        if "eligibility" in fact_id:
            scope = "eligibility"
        elif "proof_of_residency" in fact_id:
            scope = "proof_of_residency"
        elif "permit" in fact_id:
            scope = "permit"
        elif "rental" in fact_id:
            scope = "rental"
        elif "leased_corporate" in fact_id:
            scope = "leased_corporate"
        elif "business" in fact_id:
            scope = "business"
        elif "military" in fact_id:
            scope = "military"
        elif "enforcement" in fact_id:
            scope = "enforcement"
        elif "office" in fact_id:
            scope = "office"
        else:
            scope = "general"

        # Use fact_id as rule_id for direct traceability
        params = {
            "rule_id": fact_id,
            "text": fact.get("text", ""),
            "fact_id": fact_id,
            "scope": scope,
            "source_url": fact.get("source_url", ""),
            "source_section": fact.get("source_section", ""),
            "last_verified": fact.get("last_verified", "2025-11-09"),
            "confidence": fact.get("confidence", "medium"),
            "note": fact.get("note", ""),
        }

        session.run(query, params)
        created_count += 1
        logger.debug(f"Created rule: {fact_id}")

    logger.info(f"Created {created_count} Rule nodes")


def create_relationships(session: Session) -> None:
    """
    Create all relationships between nodes.

    Args:
        session: Neo4j session
    """
    logger.info("Creating relationships")

    relationships = []

    # Process HAS_STEP relationships
    relationships.extend([
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp.check_eligibility'})
        MERGE (p)-[r:HAS_STEP {order: 1}]->(s)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp.gather_documents'})
        MERGE (p)-[r:HAS_STEP {order: 2}]->(s)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (s:Step {step_id: 'rpp.submit_application'})
        MERGE (p)-[r:HAS_STEP {order: 3}]->(s)
        """,
    ])

    # Step DEPENDS_ON relationships
    relationships.extend([
        """
        MATCH (s2:Step {step_id: 'rpp.gather_documents'})
        MATCH (s1:Step {step_id: 'rpp.check_eligibility'})
        MERGE (s2)-[r:DEPENDS_ON]->(s1)
        """,
        """
        MATCH (s3:Step {step_id: 'rpp.submit_application'})
        MATCH (s2:Step {step_id: 'rpp.gather_documents'})
        MERGE (s3)-[r:DEPENDS_ON]->(s2)
        """,
    ])

    # Process REQUIRES relationships (eligibility requirements)
    relationships.extend([
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (r:Requirement {requirement_id: 'rpp.req.vehicle_class'})
        MERGE (p)-[:REQUIRES]->(r)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (r:Requirement {requirement_id: 'rpp.req.ma_registration'})
        MERGE (p)-[:REQUIRES]->(r)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (r:Requirement {requirement_id: 'rpp.req.no_unpaid_tickets'})
        MERGE (p)-[:REQUIRES]->(r)
        """,
        """
        MATCH (p:Process {process_id: 'boston_resident_parking_permit'})
        MATCH (r:Requirement {requirement_id: 'rpp.req.proof_of_residency'})
        MERGE (p)-[:REQUIRES]->(r)
        """,
    ])

    # Step NEEDS_DOCUMENT relationships (gather_documents step needs proof of residency)
    doc_types = [
        "proof.utility_bill",
        "proof.cable_bill",
        "proof.bank_statement",
        "proof.mortgage_statement",
        "proof.credit_card_statement",
        "proof.water_sewer_bill",
        "proof.lease_agreement",
    ]

    for doc_type_id in doc_types:
        relationships.append(f"""
        MATCH (s:Step {{step_id: 'rpp.gather_documents'}})
        MATCH (dt:DocumentType {{doc_type_id: '{doc_type_id}'}})
        MERGE (s)-[r:NEEDS_DOCUMENT {{count: 1}}]->(dt)
        """)

    # DocumentType SATISFIES Requirement relationships
    for doc_type_id in doc_types:
        relationships.append(f"""
        MATCH (dt:DocumentType {{doc_type_id: '{doc_type_id}'}})
        MATCH (req:Requirement {{requirement_id: 'rpp.req.proof_of_residency'}})
        MERGE (dt)-[r:SATISFIES]->(req)
        """)

    # Step HANDLED_AT Office relationship
    relationships.append("""
    MATCH (s:Step {step_id: 'rpp.submit_application'})
    MATCH (o:Office {office_id: 'parking_clerk'})
    MERGE (s)-[r:HANDLED_AT]->(o)
    """)

    # Rule RULE_GOVERNS Requirement relationships
    rule_requirement_mappings = [
        ("rpp.eligibility.vehicle_class", "rpp.req.vehicle_class"),
        ("rpp.eligibility.registration_state", "rpp.req.ma_registration"),
        ("rpp.eligibility.no_unpaid_tickets", "rpp.req.no_unpaid_tickets"),
        ("rpp.proof_of_residency.count", "rpp.req.proof_of_residency"),
        ("rpp.proof_of_residency.recency", "rpp.req.proof_of_residency"),
        ("rpp.proof_of_residency.name_match", "rpp.req.proof_of_residency"),
    ]

    for rule_id, req_id in rule_requirement_mappings:
        relationships.append(f"""
        MATCH (rule:Rule {{rule_id: '{rule_id}'}})
        MATCH (req:Requirement {{requirement_id: '{req_id}'}})
        MERGE (rule)-[r:RULE_GOVERNS]->(req)
        """)

    # Execute all relationship queries
    for rel_query in relationships:
        session.run(rel_query)

    logger.info(f"Created {len(relationships)} relationships")


def seed_database(neo4j_uri: str, neo4j_user: str, neo4j_password: str, facts_path: str) -> None:
    """
    Main function to seed the Neo4j database with Boston RPP process graph.

    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        facts_path: Path to facts YAML file

    Raises:
        Exception: If database connection or seeding fails
    """
    logger.info("Starting Neo4j seeding for Boston RPP")
    logger.info(f"Connecting to Neo4j at {neo4j_uri}")

    # Load facts registry
    facts_data = load_facts_registry(facts_path)

    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        # Verify connection
        driver.verify_connectivity()
        logger.info("Neo4j connection verified")

        with driver.session() as session:
            # Create constraints first (for idempotence)
            create_constraints(session)

            # Create nodes
            create_process_node(session, facts_data)
            create_step_nodes(session)
            create_requirement_nodes(session, facts_data)
            create_document_type_nodes(session, facts_data)
            create_office_node(session, facts_data)
            create_rule_nodes(session, facts_data)

            # Create relationships
            create_relationships(session)

        logger.info("Neo4j seeding completed successfully")

    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        raise
    finally:
        driver.close()
        logger.info("Neo4j connection closed")


def main() -> int:
    """
    Entry point for the seed script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Get environment variables
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        logger.error(
            "Missing required environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
        )
        logger.error("Please set these in your .env file or environment")
        return 1

    # Determine facts file path (relative to project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    facts_path = project_root / "docs" / "facts" / "boston_rpp.yaml"

    if not facts_path.exists():
        logger.error(f"Facts file not found at {facts_path}")
        return 1

    try:
        seed_database(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            facts_path=str(facts_path),
        )
        return 0
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
