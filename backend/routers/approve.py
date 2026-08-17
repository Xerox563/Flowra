from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import SessionLocal
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id
from backend.models.task import Task
from backend.services import cache

router = APIRouter(prefix="/tasks", tags=["approve"])
logger = get_logger(__name__)


class ApprovalRequest(BaseModel):
    decision: Literal["approve", "reject"]


@router.post("/{task_id}/approve")
def approve_task(task_id: str, req: ApprovalRequest):
    trace_id = get_trace_id()

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    approval_key = f"approval:{task_id}"
    current = cache.get(approval_key)
    if current is None:
        raise HTTPException(
            status_code=400,
            detail="Task is not currently awaiting approval",
        )
    if current in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=400,
            detail=f"Task already decided: {current}",
        )

    decision_val = "APPROVED" if req.decision == "approve" else "REJECTED"
    cache.set(approval_key, decision_val, ttl_seconds=3600)

    if req.decision == "reject":
        try:
            db = SessionLocal()
            t = db.query(Task).filter(Task.id == task_id).first()
            if t:
                t.status = "FAILED"
                t.updated_at = db.func.now()
                db.commit()
            db.close()
        except Exception as e:
            logger.error("failed to mark task as rejected", extra={"error": str(e), "task_id": task_id})

    events_key = f"task_events:{task_id}"
    existing = cache.get_json(events_key) or []
    existing.append({"step": "APPROVAL", "status": decision_val, "decision": decision_val})
    cache.set_json(events_key, existing, ttl_seconds=172800)

    logger.info(
        f"approval {decision_val}",
        extra={"trace_id": trace_id, "task_id": task_id, "decision": decision_val},
    )
    return {"task_id": task_id, "decision": decision_val}
