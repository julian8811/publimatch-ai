"""Celery application instance for PubliMatch async tasks.

Uses Redis as both broker and result backend.
Gracefully handles missing Redis at import time.
"""

import logging

from celery import Celery

logger = logging.getLogger(__name__)

try:
    from app.core.config import settings

    celery_app = Celery(
        "publimatch",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
except Exception as e:
    logger.warning(
        "Failed to configure Celery: %s. Celery tasks will not be available.", e
    )
    celery_app = None  # type: ignore[assignment]
