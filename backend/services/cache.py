import json
from typing import Any, Optional

import redis

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id

logger = get_logger(__name__)

_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def get(key: str) -> Optional[str]:
    client = get_client()
    trace_id = get_trace_id()
    try:
        value = client.get(key)
        logger.debug(
            "redis get",
            extra={"trace_id": trace_id, "key": key, "found": value is not None},
        )
        return value
    except Exception as e:
        logger.error(
            "redis get failed",
            extra={"trace_id": trace_id, "key": key, "error": str(e)},
        )
        return None


def set(key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
    client = get_client()
    trace_id = get_trace_id()
    try:
        if ttl_seconds:
            client.setex(key, ttl_seconds, value)
        else:
            client.set(key, value)
        logger.debug(
            "redis set",
            extra={"trace_id": trace_id, "key": key, "ttl_seconds": ttl_seconds},
        )
    except Exception as e:
        logger.error(
            "redis set failed",
            extra={"trace_id": trace_id, "key": key, "error": str(e)},
        )


def delete(key: str) -> None:
    client = get_client()
    trace_id = get_trace_id()
    try:
        client.delete(key)
        logger.debug(
            "redis delete",
            extra={"trace_id": trace_id, "key": key},
        )
    except Exception as e:
        logger.error(
            "redis delete failed",
            extra={"trace_id": trace_id, "key": key, "error": str(e)},
        )


def get_json(key: str) -> Optional[Any]:
    raw = get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    set(key, json.dumps(value), ttl_seconds)
