.PHONY: help install install-dev test test-cov lint format type-check run clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv pip install -e .

install-dev:  ## Install dependencies including dev tools
	uv pip install -e ".[dev]"

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term

lint:  ## Run linting checks
	ruff check .

format:  ## Format code
	ruff format .

type-check:  ## Run type checking
	mypy src/

run:  ## Run development server
	uvicorn src.main:app --reload --port 8000

clean:  ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
