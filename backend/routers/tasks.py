from fastapi import APIRouter, Depends, HTTPException, Header, Response, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id, set_trace_id
from backend.models.task import Task
from backend.schemas.task import TaskCreateRequest, TaskListResponse, TaskResponse, TaskDetailResponse
from backend.services import queue, idempotency as idempotency_service

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    trace_id = get_trace_id()
    logger.info(
        "listing tasks",
        extra={"trace_id": trace_id, "page": page, "per_page": per_page},
    )
    total = db.query(Task).count()
    tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=TaskResponse)
def create_task(
    response: Response,
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    trace_id = get_trace_id()

    existing_task_id = idempotency_service.check_idempotency(idempotency_key)
    if existing_task_id:
        existing = db.query(Task).filter(Task.id == existing_task_id).first()
        if existing:
            response.status_code = 200
            if existing.trace_id:
                set_trace_id(existing.trace_id)
            return TaskResponse(
                task_id=existing.id, trace_id=existing.trace_id, status=existing.status
            )

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

    queue.publish_message(str(task.id), task.goal, trace_id)
    idempotency_service.store_idempotency(idempotency_key, str(task.id))

    logger.info(
        "task created",
        extra={
            "trace_id": trace_id,
            "task_id": str(task.id),
            "status": task.status,
        },
    )

    response.status_code = 201
    return TaskResponse(task_id=task.id, trace_id=task.trace_id, status=task.status)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    trace_id = get_trace_id()
    logger.info(
        "fetching task",
        extra={"trace_id": trace_id, "task_id": task_id},
    )

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskDetailResponse.model_validate(task)
