from typing import Optional

from backend.services import cache
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id

logger = get_logger(__name__)

IDEMPOTENCY_TTL_SECONDS = 86400


def _key(idempotency_key: str) -> str:
    return f"idempotent:{idempotency_key}"


def check_idempotency(idempotency_key: str) -> Optional[str]:
    trace_id = get_trace_id()
    if not idempotency_key:
        return None
    stored = cache.get(_key(idempotency_key))
    if stored:
        logger.info(
            "idempotency key hit returning existing task",
            extra={"trace_id": trace_id, "idempotency_key": idempotency_key, "task_id": stored},
        )
    return stored


def store_idempotency(idempotency_key: str, task_id: str) -> None:
    trace_id = get_trace_id()
    if not idempotency_key:
        return
    cache.set(_key(idempotency_key), task_id, IDEMPOTENCY_TTL_SECONDS)
    logger.info(
        "idempotency key stored",
        extra={"trace_id": trace_id, "idempotency_key": idempotency_key, "task_id": task_id},
    )
