# Boston Government Services Backend
# Uses UV package manager for Python dependencies

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    poppler-utils \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add UV to PATH (installed to /root/.local/bin)
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files first for better layer caching
# If pyproject.toml hasn't changed, Docker will use cached layers
# README.md is required by pyproject.toml's readme field
COPY pyproject.toml README.md ./

# Install Python dependencies using UV
# Use editable install for development compatibility with volume mounts
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e ".[dev]"

# Copy the rest of the application
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Set Python path to find the src module
ENV PYTHONPATH=/app

# Activate virtual environment and run uvicorn
# Note: docker-compose.yml may override this CMD for development
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
