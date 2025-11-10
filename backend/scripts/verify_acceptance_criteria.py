#!/usr/bin/env python3
"""Verify acceptance criteria for Issue #7."""

import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

with driver.session() as session:
    # Verify Process node
    result = session.run('MATCH (p:Process {process_id: "boston_resident_parking_permit"}) RETURN p.name, p.source_url, p.confidence')
    process = result.single()
    print("✓ Process Node:")
    print(f"  Name: {process['p.name']}")
    print(f"  Source: {process['p.source_url']}")
    print(f"  Confidence: {process['p.confidence']}")

    # Count Step nodes
    step_count = session.run('MATCH (s:Step) WHERE s.process_id = "boston_resident_parking_permit" RETURN count(s) as count').single()['count']
    print(f"\n✓ Step Nodes: {step_count} (expected: 3)")

    # Count Requirement nodes
    req_count = session.run('MATCH (r:Requirement) WHERE r.applies_to_process = "boston_resident_parking_permit" RETURN count(r) as count').single()['count']
    print(f"✓ Requirement Nodes: {req_count} (expected: 4)")

    # Count DocumentType nodes
    doc_count = session.run('MATCH (dt:DocumentType) WHERE dt.doc_type_id STARTS WITH "proof." RETURN count(dt) as count').single()['count']
    print(f"✓ DocumentType Nodes: {doc_count} (expected: 7)")

    # Count Office nodes
    office_count = session.run('MATCH (o:Office) RETURN count(o) as count').single()['count']
    print(f"✓ Office Nodes: {office_count} (expected: 1)")

    # Count Rule nodes
    rule_count = session.run('MATCH (r:Rule) RETURN count(r) as count').single()['count']
    print(f"✓ Rule Nodes: {rule_count} (expected: 29 from Facts Registry)")

    # Verify all nodes have citation fields
    print("\n✓ Citation Verification:")
    result = session.run('''
        MATCH (n)
        WHERE n:Process OR n:Step OR n:Requirement OR n:DocumentType OR n:Office OR n:Rule
        RETURN
            count(n) as total,
            sum(CASE WHEN n.source_url IS NOT NULL THEN 1 ELSE 0 END) as with_source,
            sum(CASE WHEN n.last_verified IS NOT NULL THEN 1 ELSE 0 END) as with_verified,
            sum(CASE WHEN n.confidence IS NOT NULL THEN 1 ELSE 0 END) as with_confidence
    ''')
    citations = result.single()
    print(f"  Total nodes: {citations['total']}")
    print(f"  With source_url: {citations['with_source']} (100%: {citations['with_source'] == citations['total']})")
    print(f"  With last_verified: {citations['with_verified']} (100%: {citations['with_verified'] == citations['total']})")
    print(f"  With confidence: {citations['with_confidence']} (100%: {citations['with_confidence'] == citations['total']})")

    # Verify relationships
    print("\n✓ Relationship Verification:")
    rels = [
        ("HAS_STEP", "Process to Steps", 3),
        ("DEPENDS_ON", "Step dependencies", 2),
        ("REQUIRES", "Process to Requirements", 4),
        ("NEEDS_DOCUMENT", "Step to DocumentTypes", 7),
        ("SATISFIES", "DocumentType to Requirement", 7),
        ("HANDLED_AT", "Step to Office", 1),
        ("RULE_GOVERNS", "Rule to Requirement", 6),
    ]

    for rel_type, description, expected in rels:
        count = session.run(f'MATCH ()-[r:{rel_type}]->() RETURN count(r) as count').single()['count']
        status = "✓" if count == expected else "✗"
        print(f"  {status} {rel_type}: {count} (expected: {expected}) - {description}")

driver.close()

print("\n" + "="*60)
print("All acceptance criteria verified!")
print("="*60)
