from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="The goal/task description")


class TaskResponse(BaseModel):
    task_id: UUID
    trace_id: str
    status: str

    class Config:
        from_attributes = True


class TaskStepResponse(BaseModel):
    id: UUID
    task_id: UUID
    step_name: str
    status: str
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    output: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskListItem(BaseModel):
    id: UUID
    trace_id: str
    goal: str
    status: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskListItem]
    total: int
    page: int
    per_page: int


class TaskDetailResponse(BaseModel):
    id: UUID
    trace_id: str
    goal: str
    status: str
    result: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    created_at: datetime
    updated_at: datetime
    steps: list[TaskStepResponse] = []

    class Config:
        from_attributes = True
