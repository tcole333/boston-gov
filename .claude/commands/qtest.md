# /qtest — Test Planning & Gaps

**Trigger:** Message begins with `#qtest` **or** PR has label `needs-tests`.  
**Goal:** List missing tests for the current diff and generate focused examples.

## Inputs (read-only)
- Current diff / changed files.
- Test suites (`backend/tests`, `frontend/tests`).
- Schema/docs needed for assertions.

## Steps
1. Map changed modules → expected unit/integration tests.
2. List gaps (missing tests/fixtures/mocks).
3. Generate **minimal** example tests (Python `pytest`, TS `Vitest`) for gaps.
4. If regulatory logic changed, include **fact assertions** (e.g., required_count = 1, freshness_days = 30).

## Output
QTEST — Required Tests

Backend:

 test_parse_rpp_requirements: asserts required_count=1, freshness_days=30

 ...

Frontend:

 DocumentUpload rejects >30-day proofs

## Guardrails
- Keep examples runnable; don’t add external services.
- No golden files for regulatory content; assert against Facts Registry accessors.
