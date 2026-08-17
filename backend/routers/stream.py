import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core.database import SessionLocal
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id
from backend.models.task import Task
from backend.services import cache

router = APIRouter(prefix="/tasks", tags=["stream"])
logger = get_logger(__name__)


def _sse_format(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.get("/{task_id}/stream")
def stream_task_events(task_id: str):
    trace_id = get_trace_id()
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(
        "SSE stream connected",
        extra={"trace_id": trace_id, "task_id": task_id},
    )

    events_key = f"task_events:{task_id}"
    state_key = f"task_state:{task_id}"
    sent_idx = 0
    last_keepalive = time.time()

    def event_generator():
        nonlocal sent_idx, last_keepalive
        timeout_s = 1800
        start = time.time()

        while (time.time() - start) < timeout_s:
            now = time.time()

            events = cache.get_json(events_key) or []
            while sent_idx < len(events):
                ev = events[sent_idx]
                sent_idx += 1
                yield _sse_format(ev)

            state = cache.get_json(state_key) or {}
            status = state.get("status", task.status)
            if status in ("COMPLETED", "FAILED"):
                remaining = events[sent_idx:]
                for ev in remaining:
                    yield _sse_format(ev)
                    sent_idx += 1
                break

            if (now - last_keepalive) > 15:
                yield _sse_format({"type": "keepalive", "timestamp": now})
                last_keepalive = now

            time.sleep(1)

        logger.info(
            "SSE stream closed",
            extra={"trace_id": trace_id, "task_id": task_id, "sent_events": sent_idx},
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
