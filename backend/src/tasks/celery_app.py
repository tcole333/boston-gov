"""
Celery application for async task processing.

This module initializes the Celery app for background tasks like
document parsing, OCR processing, and validation.
"""

import os

from celery import Celery

# Get configuration from environment variables
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Initialize Celery app
celery_app = Celery(
    "boston_gov",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks from src.tasks module
celery_app.autodiscover_tasks(["src.tasks"])


# Example task placeholder (will be replaced with actual tasks)
@celery_app.task(name="tasks.health_check")
def health_check() -> dict[str, str]:
    """
    Health check task to verify Celery worker is functioning.

    Returns:
        dict: Status message
    """
    return {"status": "healthy", "message": "Celery worker is operational"}
