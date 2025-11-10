# Changelog

All notable changes to the Boston Government Navigator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Boston Resident Parking Permit (RPP) process implementation
- Claude SDK agent for conversational guidance with native tool calling
- Neo4j graph database schema for process mapping
- Vector store integration for regulatory document retrieval
- FastAPI backend with chat endpoints
- React frontend with chat interface and process visualization

## [0.1.0] - 2025-11-09

### Added
- Initial project scaffolding and structure
- Project documentation:
  - `CLAUDE.md` - Operating rules and conventions for AI agents
  - `docs/PRD.md` - Product Requirements Document
  - `docs/architecture.md` - Technical architecture overview
  - `docs/data_model.md` - Graph database schema design
  - `docs/facts/boston_rpp.yaml` - Boston RPP regulatory facts
- Configuration files:
  - `.gitignore` - Git ignore patterns for Python, Node.js, and project-specific files
  - `docker-compose.yml` - Multi-service Docker setup (Neo4j, Redis, backend, frontend, Celery)
  - `.pre-commit-config.yaml` - Pre-commit hooks for code quality (Ruff, mypy, Prettier, ESLint)
- Data directory structure:
  - `data/raw/` - For scraped documents (gitignored)
  - `data/processed/` - For structured/parsed data
  - `data/feedback/` - For user feedback collection
- Research documentation:
  - `research/resident_parking_permit.md` - Initial RPP process research
- Development infrastructure setup:
  - Neo4j graph database configuration
  - Redis for Celery task queue
  - Backend service configuration
  - Frontend development server configuration
  - Celery worker for async document processing

### Technical Decisions
- **Backend**: Python 3.11+ with FastAPI for API layer
- **Frontend**: React + TypeScript with Vite build tool
- **Graph DB**: Neo4j for regulatory process graph
- **Vector Store**: Pinecone (with pgvector as alternative)
- **Agent Framework**: Anthropic Claude SDK for multi-step agent orchestration with native tool calling
- **Task Queue**: Celery + Redis for async processing
- **Testing**: pytest (backend), Vitest (frontend)
- **Code Quality**: Ruff + mypy (Python), ESLint + Prettier (TypeScript)

### Repository
- Initialized Git repository
- GitHub integration ready
- GitHub Issues/Projects workflow for state management

---

## Version History Notes

### Versioning Strategy
- **Major (X.0.0)**: Breaking changes, major feature releases
- **Minor (0.X.0)**: New features, process additions, backward-compatible changes
- **Patch (0.0.X)**: Bug fixes, documentation updates, minor improvements

### Release Process
1. Update CHANGELOG.md with all changes since last release
2. Update version numbers in `backend/pyproject.toml` and `frontend/package.json`
3. Create git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. Push tag: `git push origin vX.Y.Z`
5. Create GitHub Release with changelog excerpt
