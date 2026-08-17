from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
def health():
    trace_id = get_trace_id()
    logger.info("health check requested", extra={"trace_id": trace_id})
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    trace_id = get_trace_id()
    checks = {"db": False, "redis": False}
    errors = []

    try:
        db.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception as e:
        errors.append(f"db: {str(e)}")

    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        errors.append(f"redis: {str(e)}")

    ready = all(checks.values())
    logger.info(
        "readiness check",
        extra={"trace_id": trace_id, "status": "ready" if ready else "not_ready", "checks": checks},
    )

    if ready:
        return {"status": "ok", "checks": checks}
    return {"status": "not_ready", "checks": checks, "errors": errors}, 503
