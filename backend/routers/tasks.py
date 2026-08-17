from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id
from backend.models.task import Task
from backend.schemas.task import TaskCreateRequest, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    trace_id = get_trace_id()
    logger.info(
        "creating task",
        extra={"trace_id": trace_id, "goal": request.goal},
    )

    task = Task(
        trace_id=trace_id,
        goal=request.goal,
        status="QUEUED",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(
        "task created",
        extra={
            "trace_id": trace_id,
            "task_id": str(task.id),
            "status": task.status,
        },
    )

    return TaskResponse(task_id=task.id, trace_id=task.trace_id, status=task.status)
