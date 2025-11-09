"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__

app = FastAPI(
    title="Boston Government Services Assistant API",
    description="Backend API for navigating government processes, starting with Boston Resident Parking Permits",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
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
