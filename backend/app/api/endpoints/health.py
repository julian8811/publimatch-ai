from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.db.database import engine
from app.core.config import settings
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return service health status including database and Redis connectivity."""
    timestamp = datetime.now(timezone.utc).isoformat()
    status = "ok"

    # Database check
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
        status = "degraded"

    # Redis check
    redis_status = "not_configured"
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
            redis_status = "connected"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_status = "disconnected"
            if status != "degraded":
                status = "degraded"

    # Gemini API key presence (not the actual key)
    gemini_status = "configured" if settings.GEMINI_API_KEY else "not_configured"

    return {
        "status": status,
        "version": "0.1.0",
        "timestamp": timestamp,
        "database": db_status,
        "redis": redis_status,
        "gemini": gemini_status,
    }
