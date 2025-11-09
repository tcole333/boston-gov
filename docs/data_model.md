# Data Model

**Version**: 1.0
**Last Updated**: 2025-11-09

---

## Overview

This document defines the Neo4j property graph schema for modeling government processes. The graph captures:

1. **Process structure** (steps, dependencies, branches)
2. **Regulatory requirements** (eligibility, documents, rules)
3. **Operational details** (offices, timing, costs)
4. **Provenance** (sources, verification dates, confidence)

All nodes include metadata for tracing to official sources (`source_url`, `last_verified`, `confidence`).

---

## Design Principles

1. **Atomic Rules**: Each regulatory fact is a separate `Rule` node
2. **Explicit Dependencies**: Use edges to model "Step A requires Step B"
3. **Temporal Tracking**: All nodes carry `created_at`, `updated_at`
4. **Citation-First**: No regulatory claim without `source_url`
5. **Confidence Scores**: `high` (official source), `medium` (inferred), `low` (ambiguous)

---

## Node Labels

### Core Process Nodes

#### `Process`
High-level government service (e.g., "Boston Resident Parking Permit").

**Properties:**
- `process_id` (string, unique): Identifier (e.g., `"boston_rpp"`)
- `name` (string): Display name
- `description` (string): One-sentence summary
- `category` (string): E.g., `"permits"`, `"licenses"`, `"benefits"`
- `jurisdiction` (string): E.g., `"City of Boston"`
- `source_url` (string): Primary official page
- `last_verified` (date): YYYY-MM-DD
- `confidence` (enum): `high`, `medium`, `low`
- `created_at` (datetime)
- `updated_at` (datetime)

#### `Step`
Actionable task within a process (e.g., "Gather proof of residency").

**Properties:**
- `step_id` (string, unique): E.g., `"rpp.gather_proof"`
- `process_id` (string): Parent process
- `name` (string): Short label
- `description` (string): Full action description
- `order` (int): Sequence number (for display)
- `estimated_time_minutes` (int): Official estimate
- `observed_time_minutes` (int): Median from user feedback
- `cost_usd` (float): If applicable
- `optional` (boolean): Can be skipped?
- `source_url` (string)
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

#### `Requirement`
Eligibility condition or rule (e.g., "MA registration at Boston address").

**Properties:**
- `requirement_id` (string, unique): E.g., `"rpp.req.ma_registration"`
- `text` (string): Human-readable description
- `fact_id` (string): Reference to Facts Registry (e.g., `"rpp.eligibility.registration_state"`)
- `applies_to_process` (string): Process ID
- `hard_gate` (boolean): Blocks progress if not met?
- `source_url` (string)
- `source_section` (string): Page/PDF section
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

#### `Rule`
Atomic regulatory fact (e.g., "Proof of residency d30 days").

**Properties:**
- `rule_id` (string, unique): E.g., `"RPP-15-4A"`
- `text` (string): Exact regulation text
- `fact_id` (string): Reference to Facts Registry
- `scope` (string): E.g., `"general"`, `"rental"`, `"military"`
- `source_url` (string): PDF or webpage
- `source_section` (string): Section/page number
- `effective_date` (date): When rule took effect
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

---

### Document & Evidence Nodes

#### `DocumentType`
Template for accepted documents (e.g., "Utility bill d30 days").

**Properties:**
- `doc_type_id` (string, unique): E.g., `"proof.utility_bill"`
- `name` (string): Display name
- `freshness_days` (int): Max age (e.g., `30`)
- `name_match_required` (boolean): Must match applicant name?
- `address_match_required` (boolean): Must match Boston address?
- `examples` (string[]): E.g., `["National Grid bill", "Eversource bill"]`
- `source_url` (string)
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

#### `Document` (User-Provided)
Instance of a user-uploaded document.

**Properties:**
- `doc_id` (string, unique): UUID
- `doc_type_id` (string): Reference to `DocumentType`
- `issuer` (string): E.g., `"National Grid"`
- `issue_date` (date): From OCR
- `name_on_doc` (string): From OCR
- `address_on_doc` (string): From OCR
- `file_ref` (string): S3/local path (deleted after 24h)
- `verified` (boolean): Passed validation?
- `validation_errors` (string[]): If any
- `created_at` (datetime)
- `deleted_at` (datetime): Auto-set to `created_at + 24h`

---

### Location & Office Nodes

#### `Office`
Physical location for in-person steps.

**Properties:**
- `office_id` (string, unique): E.g., `"parking_clerk"`
- `name` (string): E.g., `"Office of the Parking Clerk"`
- `address` (string): Full street address
- `room` (string): Room number (e.g., `"224"`)
- `hours` (string): E.g., `"Mon-Fri, 9:00-4:30"`
- `phone` (string)
- `email` (string)
- `source_url` (string)
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

#### `RPPNeighborhood`
Boston parking neighborhood (RPP-specific).

**Properties:**
- `nbrhd_id` (string, unique): E.g., `"back_bay"`
- `name` (string): Display name
- `auto_renew_cycle` (date): Next audit date
- `posted_streets` (string[]): Street names with RPP signage
- `notes` (string): Special rules
- `source_url` (string)
- `last_verified` (date)
- `confidence` (enum)
- `created_at` (datetime)
- `updated_at` (datetime)

---

### Resource Nodes

#### `WebResource`
Official URL (page, PDF, portal).

**Properties:**
- `res_id` (string, unique): E.g., `"howto"`
- `title` (string): Page title
- `url` (string, unique): Full URL
- `type` (enum): `how_to`, `program`, `portal`, `pdf_form`
- `owner` (string): E.g., `"Parking Clerk"`, `"BTD"`
- `last_seen` (date): Last successful fetch
- `hash` (string): SHA256 of content (for change detection)
- `created_at` (datetime)
- `updated_at` (datetime)

---

### User & Application Nodes (Phase 2+)

#### `Person`
User (optional, for tracking).

**Properties:**
- `person_id` (string, unique): UUID
- `email` (string): Hashed
- `created_at` (datetime)

#### `Application`
User's process session.

**Properties:**
- `app_id` (string, unique): UUID
- `process_id` (string): E.g., `"boston_rpp"`
- `category` (enum): `new`, `renewal`, `replacement`, `rental`, etc.
- `submitted_on` (datetime)
- `status` (enum): `pending`, `approved`, `denied`
- `reason_if_denied` (string)
- `created_at` (datetime)
- `updated_at` (datetime)

---

## Relationships (Edges)

### Process Structure

| Edge Type | From ’ To | Properties | Description |
|-----------|-----------|------------|-------------|
| `HAS_STEP` | Process ’ Step | `order` (int) | Process contains steps |
| `DEPENDS_ON` | Step ’ Step | `condition` (string) | Step B requires Step A |
| `BRANCHES_ON` | Step ’ Step | `condition` (string) | Conditional branch |

### Requirements & Rules

| Edge Type | From ’ To | Properties | Description |
|-----------|-----------|------------|-------------|
| `REQUIRES` | Process ’ Requirement | | Process has eligibility gate |
| `RULE_GOVERNS` | Rule ’ Requirement | | Rule defines requirement |
| `EXCEPTION_FOR` | Rule ’ Category | `category` (string) | Rule exception (e.g., military) |

### Documents

| Edge Type | From ’ To | Properties | Description |
|-----------|-----------|------------|-------------|
| `NEEDS_DOCUMENT` | Step ’ DocumentType | `count` (int) | How many of this type? |
| `SATISFIES` | DocumentType ’ Requirement | | Document proves requirement |
| `PROVIDED` | Person ’ Document | | User uploaded doc |

### Locations & Resources

| Edge Type | From ’ To | Properties | Description |
|-----------|-----------|------------|-------------|
| `HANDLED_AT` | Step ’ Office | | In-person step location |
| `USES_RESOURCE` | Step ’ WebResource | | Link to portal/form |
| `APPLIES_IN` | Process ’ RPPNeighborhood | | Process scope (RPP-specific) |

### Applications (Phase 2+)

| Edge Type | From ’ To | Properties | Description |
|-----------|-----------|------------|-------------|
| `SUBMITTED` | Person ’ Application | | User started process |
| `REQUESTS` | Application ’ Process | | What they're applying for |

---

## Constraints

```cypher
CREATE CONSTRAINT process_id_unique IF NOT EXISTS FOR (p:Process) REQUIRE p.process_id IS UNIQUE;
CREATE CONSTRAINT step_id_unique IF NOT EXISTS FOR (s:Step) REQUIRE s.step_id IS UNIQUE;
CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.requirement_id IS UNIQUE;
CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE;
CREATE CONSTRAINT doc_type_id_unique IF NOT EXISTS FOR (dt:DocumentType) REQUIRE dt.doc_type_id IS UNIQUE;
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
CREATE CONSTRAINT office_id_unique IF NOT EXISTS FOR (o:Office) REQUIRE o.office_id IS UNIQUE;
CREATE CONSTRAINT web_resource_url_unique IF NOT EXISTS FOR (w:WebResource) REQUIRE w.url IS UNIQUE;
CREATE CONSTRAINT nbrhd_id_unique IF NOT EXISTS FOR (n:RPPNeighborhood) REQUIRE n.nbrhd_id IS UNIQUE;
CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT app_id_unique IF NOT EXISTS FOR (a:Application) REQUIRE a.app_id IS UNIQUE;
```

---

## Indexes

```cypher
CREATE INDEX process_category IF NOT EXISTS FOR (p:Process) ON (p.category);
CREATE INDEX step_process IF NOT EXISTS FOR (s:Step) ON (s.process_id);
CREATE INDEX requirement_fact IF NOT EXISTS FOR (r:Requirement) ON (r.fact_id);
CREATE INDEX rule_scope IF NOT EXISTS FOR (r:Rule) ON (r.scope);
CREATE INDEX doc_type_freshness IF NOT EXISTS FOR (dt:DocumentType) ON (dt.freshness_days);
CREATE INDEX web_resource_type IF NOT EXISTS FOR (w:WebResource) ON (w.type);
```

---

## Example Queries

### 1. Get all steps for a process (in order)

```cypher
MATCH (p:Process {process_id: 'boston_rpp'})-[:HAS_STEP]->(s:Step)
RETURN s
ORDER BY s.order ASC;
```

### 2. Find hard-gate requirements

```cypher
MATCH (p:Process {process_id: 'boston_rpp'})-[:REQUIRES]->(r:Requirement {hard_gate: true})
OPTIONAL MATCH (rule:Rule)-[:RULE_GOVERNS]->(r)
RETURN r.text, rule.source_url;
```

### 3. Get accepted document types for a step

```cypher
MATCH (s:Step {step_id: 'rpp.gather_proof'})-[:NEEDS_DOCUMENT]->(dt:DocumentType)
RETURN dt.name, dt.freshness_days, dt.examples;
```

### 4. Trace a requirement back to its official source

```cypher
MATCH (r:Requirement {requirement_id: 'rpp.req.ma_registration'})<-[:RULE_GOVERNS]-(rule:Rule)
RETURN rule.text, rule.source_url, rule.source_section, rule.last_verified;
```

### 5. Find all stale facts (not verified in >90 days)

```cypher
MATCH (n)
WHERE n.last_verified < date() - duration({days: 90})
RETURN labels(n), n.source_url, n.last_verified
ORDER BY n.last_verified ASC;
```

---

## Seed Data Example (Boston RPP)

See `/research/resident_parking_permit.md` Section 8 for detailed seed data.

**Minimal seed** (Cypher):

```cypher
// Process
CREATE (rpp:Process {
  process_id: 'boston_rpp',
  name: 'Boston Resident Parking Permit',
  description: 'Obtain a neighborhood-specific parking permit for your MA-registered vehicle',
  category: 'permits',
  jurisdiction: 'City of Boston',
  source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

// Steps
CREATE (s1:Step {
  step_id: 'rpp.check_eligibility',
  process_id: 'boston_rpp',
  name: 'Check eligibility',
  description: 'Confirm vehicle class, MA registration, and address',
  order: 1,
  estimated_time_minutes: 5,
  cost_usd: 0.0,
  source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

CREATE (s2:Step {
  step_id: 'rpp.gather_proof',
  process_id: 'boston_rpp',
  name: 'Gather proof of residency',
  description: 'Obtain one accepted document dated d30 days',
  order: 2,
  estimated_time_minutes: 15,
  cost_usd: 0.0,
  source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

CREATE (s3:Step {
  step_id: 'rpp.apply',
  process_id: 'boston_rpp',
  name: 'Submit application',
  description: 'Apply online or in person at City Hall',
  order: 3,
  estimated_time_minutes: 20,
  cost_usd: 0.0,
  source_url: 'https://www.boston.gov/parkingpermits',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

// Link process to steps
CREATE (rpp)-[:HAS_STEP {order: 1}]->(s1);
CREATE (rpp)-[:HAS_STEP {order: 2}]->(s2);
CREATE (rpp)-[:HAS_STEP {order: 3}]->(s3);

// Step dependencies
CREATE (s2)-[:DEPENDS_ON]->(s1);
CREATE (s3)-[:DEPENDS_ON]->(s2);

// Requirements
CREATE (req1:Requirement {
  requirement_id: 'rpp.req.ma_registration',
  text: 'Valid Massachusetts registration in your name at your Boston address',
  fact_id: 'rpp.eligibility.registration_state',
  applies_to_process: 'boston_rpp',
  hard_gate: true,
  source_url: 'https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf',
  source_section: 'Section 15, Rule 15-4A',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

CREATE (rpp)-[:REQUIRES]->(req1);

// DocumentType
CREATE (dt1:DocumentType {
  doc_type_id: 'proof.utility_bill',
  name: 'Utility bill (gas/electric/phone)',
  freshness_days: 30,
  name_match_required: true,
  address_match_required: true,
  examples: ['National Grid', 'Eversource', 'Verizon'],
  source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

CREATE (s2)-[:NEEDS_DOCUMENT {count: 1}]->(dt1);

// Office
CREATE (office:Office {
  office_id: 'parking_clerk',
  name: 'Office of the Parking Clerk',
  address: '1 City Hall Square, Boston MA 02201',
  room: '224',
  hours: 'Mon-Fri, 9:00-4:30',
  phone: '617-635-4410',
  email: 'parking@boston.gov',
  source_url: 'https://www.boston.gov/departments/parking-clerk',
  last_verified: date('2025-11-09'),
  confidence: 'high',
  created_at: datetime(),
  updated_at: datetime()
});

CREATE (s3)-[:HANDLED_AT]->(office);
```

---

## References

- **Research**: `/research/resident_parking_permit.md` (Sections 2, 3, 7)
- **Facts Registry**: `/docs/facts/boston_rpp.yaml`
- **Architecture**: `/docs/architecture.md`
