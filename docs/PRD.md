
---

### `PRD.md` (replace your file)

```md
# Product Requirements Document (PRD)
## Government Services Navigation Assistant

**Version**: 1.1
**Last Updated**: 2025-11-09
**Note**: See GitHub Issues/Projects for current project status and active milestone

---

## Executive Summary

### Vision
Make government services legible and navigable by mapping processes as graphs and guiding users through personalized, cited steps.

### Problem
Requirements are scattered; dependencies are opaque; timelines vary; informal practices aren’t documented; users waste time and trips.

### Success Criteria
1. **User Success:** ≥80% complete intended process on first attempt  
2. **Time Savings:** ≥50% reduction in research time  
3. **Accuracy:** ≥95% correct requirements (validated via feedback)  
4. **Trust:** ≥70% report confidence in guidance  
5. **Engagement:** ≥60% provide post‑process feedback

---

## Target Users
Primary: new residents; small businesses with simple permits; residents with limited time/information.  
Secondary: policy researchers, journalists, reform advocates.  
Out of scope (Phase 1): professional services (lawyers/expediters), B2B.

---

## Product Capabilities — Phase 1: Boston RPP (3 months)

### 1. Process Discovery via Chat
Natural multi‑turn chat narrows from “I need a permit” to the correct RPP variant and path.  
**Acceptance:** Identifies correct variant within ≤5 questions for ≥90% of users; supports ≥20 situations.

### 2. Dynamic Process Visualization (DAG)
Real‑time, interactive graph (steps, deps, current/next).  
**Acceptance:** Renders <2s; nodes clickable; mobile‑friendly; status color‑keyed.

### 3. Step‑by‑Step Guidance
For each step: action description; required documents with examples; office/website details; estimated time (official + observed); cost; common mistakes; dependencies.  
**Acceptance:** All steps complete; links valid; examples specific; warnings grounded in feedback.

### 4. Source Citation & Verification
Every **regulatory** claim includes `source_url`, optional `source_section`, `last_verified`, `confidence`, and provenance (human/agent/community).  
**Acceptance:** 100% of claims cited; links validated; confidence calibrated; citations visible inline.

### 5. Document Upload & Parsing
Upload PDF/JPG/PNG; OCR when needed; validate **name**, **Boston address**, and **recency**.  
**Acceptance:** 90% document‑type accuracy; clear pass/fail feedback; auto‑delete within 24h.

> **Note**: All Boston RPP regulatory facts (proof count, recency requirements, timing, costs) are defined in `/docs/facts/boston_rpp.yaml` with full source citations. Reference fact IDs: `rpp.proof_of_residency.count`, `rpp.proof_of_residency.recency`, `rpp.permit.mail_timing`, `rpp.permit.in_person_timing`, `rpp.permit.cost`.

### 6. Feedback Collection
Thumbs up/down per step, quick issue reports, and a short post‑completion survey.  
**Acceptance:** ≥60% survey response; feedback categorized; estimates updated after ≥5 consistent reports.

---

## Technical Requirements

### Data Collection & Structuring
- **Sources:** Boston.gov RPP pages and PDFs; RMV prerequisites; user feedback.
- **Graph (Neo4j):** Nodes = Process, Step, Office, Document, Requirement; Edges = REQUIRES, HAS_STEP, HANDLED_BY, NEEDS_DOCUMENT.
- **Vector (PostgreSQL + pgvector):** Embeddings for RAG-based semantic search over regulations.
- **Properties:** timestamps, `source_url`, `last_verified`, `confidence`.

### LLM Agents
- **Parser Agent:** HTML/PDF → structured JSON; confidence + citations; flags ambiguity.  
- **Conversation Agent:** Contexted Q&A; queries graph; handles edge cases.  
- **Validation Agent:** Schema validation; contradiction detection; stale link detection.

### API Endpoints
POST /api/chat/message
GET /api/processes/{id}
POST /api/processes/{id}/start
GET /api/processes/{id}/steps/{step_id}
POST /api/documents/upload
POST /api/feedback
GET /api/processes/{id}/dag


### Frontend Components
`<ChatInterface>` · `<ProcessDAG>` · `<StepDetail>` · `<DocumentUpload>` · `<FeedbackForm>`

---

## Non‑Functional

**Performance:** chat p95 <3s; page load <2s; DAG <2s (≤50 nodes); doc processing <10s; API uptime 99.5%.  
**Scalability:** ≥1000 concurrent users (Phase 1).  
**Accessibility:** WCAG 2.1 AA, keyboard‑only, 200% zoom.  
**Security/Privacy:** HTTPS; no PII without consent; 24h doc deletion; rate limiting; input sanitization; XSS/SQLi protections.  
**Browser Support:** Latest Chrome/Edge/Firefox/Safari + mobile.

---

## Source‑of‑Truth & Facts Registry (new)
- **Facts Registry:** Each regulatory fact is a record with `id`, `text`, `source_url`, `source_section`, `last_verified`, `confidence`. UI strings **bind** to these facts; agents **write** through validators that enforce citations.
- **Change Monitoring:** Nightly job hashes canonical Boston.gov pages/PDFs; on diff, open a `policy-change` Issue with a proposed patch and reviewers.
- **Acceptance:** 100% of regulatory UI copy backed by facts; diffs generate Issues automatically; median triage <48h.

---

## User Flows (corrected)

### Flow 1 — New Resident Getting an RPP
1) Chat narrows to “new RPP”.  
2) DAG shows: **[Update Registration] → [Gather Documents] → [Apply Online/In‑Person]**.  
3) System validates documents (e.g., lease + bank statement).  
4) Application guidance: links to City portal and City Hall.  
5) **Expectation:** In‑person → **same‑day**; by mail → typically **~5–10 business days**.  
6) Follow‑up: brief survey to capture actual timelines.

### Flow 2 — Missing/Contradictory Info
Users can flag steps; the system opens an Issue with source and context; maintainers review within 48h.

### Flow 3 — Roommate Utilities (edge case, corrected)
System explains **alternatives** (e.g., **lease** with your name; **bank statement** ≤ **30 days**).  
**Requirement:** **one** accepted proof of residency (≤30 days), with name/address matching the registration (or as specified by path).  
DAG updates to reflect chosen alternative.

---

## Success Metrics
User, System, Content‑health, and Impact metrics unchanged; tie “accuracy” to Facts Registry coverage.

---

## Risks & Mitigations
- **Model errors:** citations + validation + user feedback  
- **Source drift:** automated change monitoring + Issues  
- **Graph complexity:** indexing, caching, load tests  
- **Trust:** visible citations, confidence badges

---

## Out of Scope (Phase 1)
Form auto‑fill/submit; email integration; user accounts; payments; multi‑language UI; government API integrations; historical dashboards; social features.

---

## Document History
| Version | Date       | Changes                                      |
|---------|------------|----------------------------------------------|
| 1.0     | 2024‑11‑09 | Initial PRD for Phase 1 MVP                  |
| 1.1     | 2025‑11‑09 | Corrected residency proof & recency; mail/in‑person expectations; added Facts Registry + Change Monitoring; clarified state lives in GitHub |
