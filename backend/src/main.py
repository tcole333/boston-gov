"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.db.graph.client import get_neo4j_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Handles startup and shutdown of resources like database connections.
    """
    # Startup: Connect to Neo4j
    neo4j = get_neo4j_client()
    await neo4j.connect()

    yield

    # Shutdown: Close Neo4j connection
    await neo4j.close()


app = FastAPI(
    title="Boston Government Services Assistant API",
    description="Backend API for navigating government processes, starting with Boston Resident Parking Permits",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware configuration
# TODO: Configure allowed origins from environment variables in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dictionary with status and version information.
    """
    return {
        "status": "healthy",
        "version": __version__,
    }


@app.get("/health/neo4j")
async def neo4j_health_check() -> dict[str, Any]:
    """
    Neo4j-specific health check endpoint.

    Verifies connectivity to Neo4j database and returns detailed status.

    Returns:
        Dictionary with Neo4j health status including:
        - status: "healthy" or "unhealthy"
        - details: Connection information
        - error: Error message if unhealthy
    """
    neo4j = get_neo4j_client()
    return await neo4j.health_check()


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint with API information.

    Returns:
        Dictionary with welcome message and documentation links.
    """
    return {
        "message": "Boston Government Services Assistant API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
