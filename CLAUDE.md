# CLAUDE.md — Operating Rules (Stateless)

> This file is **stateless**. All plans, statuses, and work-in-progress notes live in **GitHub Issues/Projects**. Treat this as a durable operating manual for agents.

## Mission & Scope (stable)
- **Purpose:** Build a proactive assistant for government processes starting with **Boston Resident Parking Permits (RPP)**.
- **Non-goals (Phase 1):** Legal advice, browser automation/form auto-submit, emailing offices, creating user accounts.

## Where State Lives (authoritative)
- **Roadmap & status:** GitHub **Projects** board + Issues labeled `plan`, `status`, `decision`.
- **Tasks:** GitHub Issues with labels `mvp`, `parking-permit`, `backend|frontend`, `agent-task`.
- **Regulatory facts:** Stored in structured data (e.g., `/docs/facts/*.yaml`) and referenced by graph nodes with `source_url`, `source_section`, `last_verified`, `confidence`. Update via Issues; **do not** edit facts in this file.
- **Changes:** `CHANGELOG.md` + Release notes.

## Agent Pre‑Flight (must pass before editing)
1. Read open Issues in the active Milestone labeled `plan`, `status`, `decision`.
2. If PRD and Issues conflict, prefer an Issue labeled `decision`. Otherwise, open a new `decision` Issue and stop.
3. For any **regulatory claim**, attach `source_url`, `source_section` (if available), `last_verified (YYYY‑MM‑DD)`, and `confidence`.
4. **Do not** persist chain‑of‑thought; commit only verifiable facts, code, or tests.
5. **Be proactive:** Flag issues in requirements, documentation, previous work, or failing tests. Raise concerns early rather than proceeding with unclear or problematic specifications.

## Retrieval Order (deterministic)
1. Milestone → Issues (`plan`, `status`, `decision`)
2. `/docs/facts/*.yaml` (regulatory facts) and `/docs/data_model.md`
3. `/docs/architecture.md`, source files relevant to the task

## Commands (explicit triggers)
These commands are defined in `/.claude/commands/`:
- **`#qplan`** → Summarize the current plan from Issues labeled `plan`; propose exactly **one** next step with rationale.
- **`#qtest`** → List tests required by the diff; generate focused unit tests; note any missing fixtures.
- **`#qcite`** → Verify all new/changed **regulatory** claims have citations + `last_verified`; add a checklist to the PR.

## Custom Agents (specialized roles)
Custom agents are defined in `/.claude/agents/`. Invoke with `@agent-name` in conversations.

### Core Agents
- **`@product-owner`** → Strategic planning, epic/issue management, PRD alignment, regulatory drift handling, citation enforcement
- **`@developer`** → Feature implementation with 7-phase workflow (context → plan → implement → test → PR → iterate → review), UV package management, citation-first coding
- **`@regulatory-research`** → Parse regulations, extract structured facts, maintain Facts Registry, citation verification, confidence scoring

### Quality Agents
- **`@testing`** → Unit/integration tests, avoiding "reward hacking", AAA pattern, parametrized tests, coverage reporting
- **`@qa`** → Smoke tests, RBAC validation, API fuzzing, security scanning, performance checks, mutation testing
- **`@e2e-testing`** → Playwright browser automation, user journey validation, critical flows, accessibility testing

### Specialized Agents
- **`@graph-modeling`** → Neo4j schema design, Cypher query optimization, data integrity, constraint management
- **`@citation-validation`** → Verify citations in PRs, validate source URLs, check freshness, confidence calibration
- **`@devops`** → Docker Compose, CI/CD with GitHub Actions, secrets management, environment parity
- **`@ui-designer`** → Government-appropriate design tokens, WCAG 2.2 AA compliance, component design
- **`@copywriting`** → Government tone (authoritative, clear, helpful), error messages, accessibility-focused copy

### Usage Examples
```
@product-owner create an epic for Phase 1 Boston RPP implementation
@developer implement the proof-of-residency validator with citations
@regulatory-research parse the latest RPP requirements from boston.gov
@graph-modeling design the Process→Step→Requirement schema
@citation-validation verify all facts in docs/facts/boston_rpp.yaml
```

---

## Project Overview (stable)
**Purpose:** Help citizens navigate government services (starting with Boston parking permits) using LLM agents to parse regulations, build process graphs, and provide conversational guidance.

**Core value:** Map processes as graphs; give personalized, cited, step‑by‑step guidance; learn from feedback to reduce bureaucracy’s “time tax”.

**Target users:** Individuals navigating services; secondary: policy researchers, journalists, reform advocates. (B2B/professional services out of scope initially.)

## Tech

### Backend
- **Python 3.11+**, **FastAPI**
- **Neo4j** (regulatory process graph)
- **PostgreSQL + pgvector** (embeddings for RAG over regulations)
- **LLM Integration**: Anthropic Claude SDK with native tool calling (multi-step agents)
- **Queue**: Celery + Redis (async doc processing)

### Frontend
- **React + TypeScript**, Vite, shadcn/ui
- **Visualization**: D3.js or Cytoscape.js
- **State**: Zustand or React Context
- **API client**: TanStack Query

### Infrastructure
- Docker/Compose; `.env` (never committed)
- **Package Management**: `uv` (Python), `npm` (JavaScript)
- **Testing**: `pytest` (backend), **Vitest** (frontend)

## Project Structure
boston-gov/
├── backend/
│ ├── src/
│ │ ├── agents/ # LLM agent implementations
│ │ ├── api/ # FastAPI routes
│ │ ├── db/ # Database models and queries
│ │ │ ├── graph/ # Neo4j operations
│ │ │ └── vector/ # Vector store ops
│ │ ├── parsers/ # PDF/HTML/forms parsing
│ │ ├── schemas/ # Pydantic models
│ │ └── services/ # Business logic
│ ├── tests/
│ └── pyproject.toml  # UV project config (dependencies, metadata)
├── frontend/
│ ├── src/
│ │ ├── components/ # chat, dag, ui
│ │ ├── hooks/ # custom hooks
│ │ ├── lib/ # utils + API client
│ │ ├── pages/
│ │ └── types/
│ ├── tests/
│ └── package.json
├── data/
│ ├── raw/ # scraped docs (gitignored)
│ ├── processed/ # structured data
│ └── feedback/
├── research/
│ ├── process_maps/
│ └── sources/
├── docs/
│ ├── PRD.md
│ ├── architecture.md
│ └── data_model.md
└── docker-compose.yml

## Development Commands

### Backend
**IMPORTANT: This project uses UV for Python package management, NOT pip.**

```bash
# Setup (from backend/)
# Install UV if not already installed: curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv                     # Create virtual environment
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"  # Install package in editable mode with dev dependencies

# Alternatively, run commands directly with uv (no activation needed):
uv run uvicorn src.main:app --reload --port 8000
uv run pytest
```

# Dev server
uv run uvicorn src.main:app --reload --port 8000

# Tests
uv run pytest
uv run pytest -v
uv run pytest tests/test_agents.py
uv run pytest -k "test_parser"

# Lint / format / types
uv run ruff check .
uv run ruff format .
uv run mypy src/

# Add dependencies
uv add <package-name>
uv add --dev <package-name>  # for dev dependencies

# Sync dependencies from pyproject.toml
uv sync

# (If using Alembic)
uv run alembic revision --autogenerate -m "desc"
uv run alembic upgrade head

### Frontend 
npm install
npm run dev
npm test
npm run test:ui
npm run test:coverage
npm run lint
npm run format
npm run type-check
npm run build
npm run preview

### Full Stack
docker-compose up
docker-compose up --build
docker-compose down
docker-compose logs -f backend

## Code Style & Conventions (stable)
### Python

MUST use type hints on all functions

PEP 8, ruff for lint/format, mypy strict

Functions small/focused; Pydantic for validation

Docstrings (Google style); no print() for logging

Handle exceptions explicitly; no bare except:

### TypeScript

TS strict mode, functional components, arrow fns

Extract complex logic into hooks

Types in types/, not inline

ESLint + Prettier; no any (use unknown then narrow)

Components ≤ ~200 lines where practical

### Git Workflow

Branch from main; PRs only (no direct pushes)

Descriptive commits (feat:, fix:, docs:, test:…)

Run tests locally before pushing

Never commit secrets

Update this file only for durable conventions (not status)

## Testing Requirements
### Backend

Tests for agent logic and graph business rules

Mock LLM/tool calls

Test DB ops with test DB or mocks

Aim ≥ 80% coverage on core logic

Include happy-path and error cases

### Example
```python
def test_parse_rpp_requirements():
    html = load_fixture("boston_rpp.html")
    reqs = parse_requirements(html)
    assert "proof_of_residency" in reqs
    assert reqs["proof_of_residency"]["required_count"] == 1
    assert reqs["proof_of_residency"]["freshness_days"] == 30
```
### Frontend

- Test interactions (typing, clicking, nav)

- API integration via MSW

- Accessibility checks (aria/keyboard)

- E2E for critical flows

## Agent Development Guidelines

1. Citations required in structured outputs
```json
{
  "requirement": "One proof of residency (<= 30 days)",
  "source_url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
  "source_section": "Proof of Boston residency",
  "confidence": "high",
  "last_verified": "2025-11-09"
}
```
2. Include confidence scores; flag ambiguity rather than guessing.

3. Validate extracted data against schemas before storing.

4. Keep reasoning ephemeral. Use plan‑then‑execute, but do not persist chain‑of‑thought to the repo or logs; store only plans/outcomes and sources.

5. Log LLM interactions for debugging with PII redacted.

## Data Model Principles

- Nodes (e.g., Process, Step, Office, Document, Requirement, User) and edges (REQUIRES, HAS_STEP, HANDLED_BY, NEEDS_DOCUMENT…)
- All regulation‑derived data carries source, last_verified, confidence
- Use properties for simple attributes; edges for relationships
- Timestamps: created_at, updated_at on nodes

## Security & Privacy

- No PII without consent
- HTTPS only; input validation/sanitization
- Secrets via environment vars only
- Rate limiting on APIs
- Log security‑relevant events

##Accessibility

- WCAG 2.1 AA, screen‑reader support, keyboard nav
- Semantic HTML, alt text, ≥4.5:1 contrast, zoom @200%

## Performance

- Aim for fast chat responses; show loading states >500ms
- Cache parsed docs; paginate long lists; lazy‑load large DAGs

## What Not To Do (Phase 1)

No browser automation, email integration, auto‑submit, or legal advice

No scraping without checking robots.txt

No unsourced regulatory claims

## Questions or Stuck?

Requirements: docs/PRD.md

Architecture: docs/architecture.md

Data modeling: docs/data_model.md

Research notes: research/

Do not store plans or status here. Open/consult Issues instead.