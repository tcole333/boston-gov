#!/usr/bin/env python3
"""Verify the Neo4j seed data."""

import os

from neo4j import GraphDatabase

neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

with driver.session() as session:
    # Count nodes by type
    result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY label")
    print("Node Counts:")
    for record in result:
        print(f"  {record['label']}: {record['count']}")

    # Count relationships
    result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY type")
    print("\nRelationship Counts:")
    for record in result:
        print(f"  {record['type']}: {record['count']}")

    # Get total counts
    total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
    total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
    print(f"\nTotal Nodes: {total_nodes}")
    print(f"Total Relationships: {total_rels}")

driver.close()
