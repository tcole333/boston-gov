# Boston Government Navigator

A proactive AI assistant for navigating government processes, starting with Boston Resident Parking Permits (RPP).

## Overview

This project uses LLM agents to parse government regulations, build process graphs, and provide conversational, step-by-step guidance to help citizens navigate bureaucratic processes more efficiently.

### Core Value Proposition

- **Process Mapping**: Government processes represented as queryable graphs
- **Personalized Guidance**: Conversational AI that adapts to individual situations
- **Always Cited**: All regulatory information includes source URLs and verification dates
- **Feedback Loop**: Learn from user interactions to improve guidance and identify friction points

### Target Users

- **Primary**: Individuals navigating Boston government services
- **Secondary**: Policy researchers, journalists, civic reform advocates

## Tech Stack

### Backend
- **Python 3.11+** with **FastAPI** for REST API
- **Neo4j** for regulatory process graph database
- **PostgreSQL + pgvector** for vector embeddings and semantic search
- **LangGraph** for multi-step agent orchestration
- **Celery + Redis** for async document processing
- **pytest** for testing

### Frontend
- **React + TypeScript** with Vite build tool
- **shadcn/ui** component library
- **D3.js** or **Cytoscape.js** for process visualization
- **Zustand** or React Context for state management
- **TanStack Query** for API integration
- **Vitest** for testing

### Infrastructure
- **Docker Compose** for local development
- **Neo4j** (graph database)
- **Redis** (task queue and caching)
- Environment-based configuration (never commit `.env`)

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- **Docker** and **Docker Compose**
- **UV** (Python package installer) - Install via: `pip install uv`

### 1. Clone and Setup

```bash
git clone <repository-url>
cd boston-gov
cp .env.example .env  # Create and configure your .env file
```

### 2. Configure Environment

Edit `.env` and add required API keys:

```env
# LLM Providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Vector Store (choose one)
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_pinecone_env

# Neo4j (defaults for Docker setup)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis (defaults for Docker setup)
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Services with Docker

```bash
# Start all services (Neo4j, Redis, backend, frontend, Celery)
docker-compose up

# Or build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down
```

Services will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Redis**: localhost:6379

### 4. Local Development (without Docker)

#### Backend Setup

```bash
cd backend

# Create virtual environment with UV
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Start development server
uvicorn src.main:app --reload --port 8000

# Run tests
pytest
pytest -v
pytest -k "test_parser"

# Type checking and linting
mypy src/
ruff check .
ruff format .
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test
npm run test:ui
npm run test:coverage

# Type checking and linting
npm run type-check
npm run lint
npm run format

# Build for production
npm run build
npm run preview
```

## Project Structure

```
boston-gov/
├── backend/                # Python FastAPI backend
│   ├── src/
│   │   ├── agents/        # LLM agent implementations
│   │   ├── api/           # FastAPI routes
│   │   ├── db/            # Database operations
│   │   │   ├── graph/     # Neo4j queries
│   │   │   └── vector/    # Vector store operations
│   │   ├── parsers/       # PDF/HTML/form parsers
│   │   ├── schemas/       # Pydantic models
│   │   └── services/      # Business logic
│   ├── tests/
│   └── requirements.txt
├── frontend/              # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # UI components (chat, DAG, etc.)
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Utilities and API client
│   │   ├── pages/         # Route pages
│   │   └── types/         # TypeScript type definitions
│   ├── tests/
│   └── package.json
├── data/                  # Data storage
│   ├── raw/              # Scraped documents (gitignored)
│   ├── processed/        # Structured data
│   └── feedback/         # User feedback
├── docs/                  # Documentation
│   ├── PRD.md            # Product Requirements
│   ├── architecture.md   # Technical architecture
│   ├── data_model.md     # Database schema
│   └── facts/            # Regulatory facts (structured)
├── research/              # Research and process maps
├── CLAUDE.md             # AI agent operating rules
├── CHANGELOG.md          # Version history
└── docker-compose.yml    # Docker services configuration
```

## Custom Agents & Hooks

### Custom Agents

This project uses specialized AI agents for different development roles. Invoke agents in conversations with `@agent-name`.

#### Core Agents
- **`@product-owner`** - Strategic planning, epic/issue management, PRD alignment, regulatory drift handling
- **`@developer`** - Feature implementation, 7-phase workflow, UV package management, citation-first coding
- **`@regulatory-research`** - Parse regulations, extract facts, maintain Facts Registry, citation verification

#### Quality Agents
- **`@testing`** - Unit/integration tests, AAA pattern, avoiding reward hacking, coverage ≥80%
- **`@qa`** - Smoke tests, RBAC validation, API fuzzing, security scanning, performance checks
- **`@e2e-testing`** - Playwright browser automation, user journey validation, WCAG compliance

#### Specialized Agents
- **`@graph-modeling`** - Neo4j schema design, Cypher optimization, data integrity, constraints
- **`@citation-validation`** - Verify citations in PRs, validate URLs, check freshness, confidence scoring
- **`@devops`** - Docker Compose, CI/CD with GitHub Actions, secrets management
- **`@ui-designer`** - Government design tokens, WCAG 2.2 AA, USWDS patterns, component design
- **`@copywriting`** - Government-appropriate tone, error messages, plain language, accessibility

**Example Usage:**
```bash
@product-owner create an epic for Phase 1 Boston RPP implementation
@developer implement the proof-of-residency validator with citations
@regulatory-research parse the latest RPP requirements from boston.gov
@graph-modeling design the Process→Step→Requirement schema
```

### Automated Hooks

Project quality is enforced through automated hooks that run during development:

#### P0 Hooks (Critical - Block Operations)
- **`secrets-guard`** - Prevents committing .env files, API keys, credentials
- **`doc-hygiene`** - Enforces stateless documentation (blocks "TODO", "WIP", status in CLAUDE.md)
- **`citation-verification`** - Ensures all regulatory facts have source_url, last_verified, confidence

#### P1 Hooks (High Priority)
- **`quality-gate`** - Runs ruff, mypy, eslint, tsc on modified files (Stop event)
- **`regulatory-context`** - Injects citation reminder when discussing regulations
- **`test-coverage`** - Warns about missing tests for modified source files

All hooks are configured in `.claude/settings.json` and scripts in `.claude/hooks/`.

## Development Workflow

### Code Style

- **Python**: PEP 8, type hints required, Google-style docstrings
- **TypeScript**: Strict mode, functional components, arrow functions
- **Linting**: Ruff (Python), ESLint (TypeScript)
- **Formatting**: Ruff (Python), Prettier (TypeScript)
- **Type Checking**: mypy (Python), tsc (TypeScript)

### Git Workflow

1. Branch from `main` for features/fixes
2. Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, etc.
3. Run tests locally before pushing
4. Create PR for review (no direct pushes to `main`)
5. Never commit secrets or `.env` files

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Hooks include:
- Ruff (Python linting and formatting)
- mypy (Python type checking)
- Prettier (JS/TS formatting)
- ESLint (JS/TS linting)
- Secret detection
- Trailing whitespace and EOF fixes

### Testing Requirements

- **Backend**: 80%+ coverage on core logic, mock LLM calls, test with test DB
- **Frontend**: Test user interactions, mock APIs with MSW, accessibility checks
- **Integration**: E2E tests for critical user flows

### State Management

All project state (roadmap, tasks, decisions) lives in **GitHub Issues and Projects**, NOT in code or documentation. This repository contains:

- Durable operating rules (`CLAUDE.md`)
- Technical documentation (`docs/`)
- Regulatory facts with sources (`docs/facts/`)
- Code and tests

## Documentation

- **Product Requirements**: [docs/PRD.md](/Users/travcole/projects/boston-gov/docs/PRD.md)
- **Architecture**: [docs/architecture.md](/Users/travcole/projects/boston-gov/docs/architecture.md)
- **Data Model**: [docs/data_model.md](/Users/travcole/projects/boston-gov/docs/data_model.md)
- **AI Agent Rules**: [CLAUDE.md](/Users/travcole/projects/boston-gov/CLAUDE.md)
- **Version History**: [CHANGELOG.md](/Users/travcole/projects/boston-gov/CHANGELOG.md)

## Regulatory Data

All regulatory information includes:
- `source_url`: Link to official source
- `source_section`: Specific section/heading (if applicable)
- `last_verified`: Date of last verification (YYYY-MM-DD)
- `confidence`: Confidence level (high/medium/low)

See [docs/facts/boston_rpp.yaml](/Users/travcole/projects/boston-gov/docs/facts/boston_rpp.yaml) for an example.

## Phase 1 Scope

Focus: **Boston Resident Parking Permit (RPP)**

Included:
- Parse RPP regulations and requirements
- Build process graph in Neo4j
- Conversational agent for step-by-step guidance
- Document requirement validation
- Process visualization

NOT Included (Phase 1):
- Browser automation or form auto-submit
- Email integration with government offices
- Legal advice or guarantees
- Account creation or authentication
- Multiple processes beyond RPP

## Security and Privacy

- No PII collected without explicit consent
- HTTPS only in production
- Input validation and sanitization
- Rate limiting on all APIs
- Secrets via environment variables only
- Security events logged (PII redacted)

## Accessibility

- WCAG 2.1 AA compliance
- Screen reader support
- Keyboard navigation
- Semantic HTML
- 4.5:1 color contrast minimum
- Zoom support up to 200%

## Contributing

1. Check open Issues in the active Milestone
2. For regulatory changes, attach sources and verification dates
3. Run tests and linting before committing
4. Follow code style conventions
5. Update CHANGELOG.md for notable changes

## License

[TBD]

## Questions or Issues?

- Create a GitHub Issue for bugs, features, or questions
- Label issues appropriately: `bug`, `feature`, `question`, `decision`
- For regulatory fact disputes, include sources and verification steps
