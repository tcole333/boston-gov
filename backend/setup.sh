#!/bin/bash
# Quick setup script for boston-gov-backend

set -e

echo "Boston Government Services Assistant - Backend Setup"
echo "====================================================="
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "Error: UV package manager not found."
    echo "Please install UV: https://github.com/astral-sh/uv"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "UV found: $(uv --version)"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python found: $(python3 --version)"

# Verify Python >= 3.11
if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
    echo "Error: Python 3.11 or higher required (found $PYTHON_VERSION)"
    exit 1
fi
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Created .env - please update with your configuration"
else
    echo ".env file already exists"
fi
echo ""

# Install dependencies
echo "Installing dependencies..."
uv pip install -e ".[dev]"
echo ""

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env with your configuration"
echo "  2. Start the development server: make run"
echo "  3. Run tests: make test"
echo "  4. View API docs: http://localhost:8000/docs"
echo ""
echo "For more commands, run: make help"
