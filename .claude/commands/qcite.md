# /qcite — Citation Verification

**Trigger:** Message begins with `#qcite` **or** PR label `needs-citation`.  
**Goal:** Ensure all **regulatory** claims added/changed in the diff have citations + `last_verified`.

## Inputs (read-only)
- Current diff, especially JSON/YAML facts and user-facing copy.
- Facts Registry accessors.

## Steps
1. Scan the diff for added/changed regulatory statements.
2. For each, check presence of:
   - `source_url` (official page/PDF)
   - `source_section` (if available)
   - `last_verified` (YYYY‑MM‑DD)
   - `confidence` (high/medium/low)
3. If missing, list items and propose fixes with suggested sources.

## Output
QCITE — Findings

Missing: /docs/facts/boston_rpp.yaml: proof_of_residency.last_verified

Suggest: source_url=https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit
 (Proof of Boston residency); last_verified=2025-11-09

## Guardrails
- Prefer **official** sources; avoid forums/social media for regulatory facts.
- If sources conflict, open a `policy-change` Issue with both links and summary.
