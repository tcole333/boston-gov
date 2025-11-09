# Boston Government Services Assistant - Backend

Backend API for the Boston Government Services Assistant, helping citizens navigate government processes starting with Boston Resident Parking Permits.

## Setup

### Prerequisites

- Python 3.11 or higher
- [UV](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Install dependencies using UV
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"
```

### Running the Development Server

```bash
# Start the FastAPI server
uvicorn src.main:app --reload --port 8000
```

The API will be available at:
- http://localhost:8000 - Root endpoint
- http://localhost:8000/docs - Swagger UI documentation
- http://localhost:8000/redoc - ReDoc documentation
- http://localhost:8000/health - Health check endpoint

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run tests matching a pattern
pytest -k "test_health"
```

### Code Quality

```bash
# Lint with ruff
ruff check .

# Format with ruff
ruff format .

# Type check with mypy
mypy src/
```

### Project Structure

```
backend/
├── src/
│   ├── agents/          # LLM agent implementations
│   ├── api/             # FastAPI route handlers
│   ├── db/
│   │   ├── graph/       # Neo4j operations
│   │   └── vector/      # Vector store ops
│   ├── parsers/         # PDF/HTML/forms parsing
│   ├── schemas/         # Pydantic models
│   ├── services/        # Business logic
│   └── main.py          # FastAPI application entry point
├── tests/               # Test suite
└── pyproject.toml       # Project configuration
```

## Architecture

See [/docs/architecture.md](../docs/architecture.md) for detailed architecture documentation.

## Contributing

Follow the code style and testing requirements outlined in [/CLAUDE.md](../CLAUDE.md).

### Key Principles

- All functions must use type hints
- Follow PEP 8 conventions
- Use Pydantic for validation
- Include docstrings (Google style)
- Handle exceptions explicitly
- Aim for 80%+ test coverage on core logic
- All regulatory claims must include citations with source_url, source_section, last_verified, and confidence

## License

MIT
