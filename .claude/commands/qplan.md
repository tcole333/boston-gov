# /qplan — Planning Ritual (Stateless)

**Trigger:** Message begins with `#qplan` **or** active Issue labeled `plan`.  
**Goal:** Produce a one‑step actionable plan sourced from GitHub Issues/Project state.

## Inputs (read-only)
- GitHub Issues labeled `plan`, `status`, `decision` in the active Milestone.
- Related code/docs referenced by those Issues.

## Steps
1. Read Issues labeled `plan` and `decision`; summarize the current objective and blockers.
2. Identify the **single next step** that unblocks maximal downstream work.
3. Emit a short plan (**≤5 bullets**) with:
   - Goal, dependencies, acceptance criteria, expected artifacts.
4. Link Issue IDs you used. If contradictions exist, open a `decision` Issue and stop.

## Output (post as a comment or PR body block)
### QPLAN — Proposed Next Step
- Goal:
- Why this next:
- Dependencies:
- Acceptance criteria:
- Links: #123, #456

## Guardrails
- Do **not** invent status; only read Issues/Project.
- If GitHub is unavailable, open an Issue explaining the block.