import uuid
from contextvars import ContextVar
from typing import Optional

trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def generate_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex[:12]}"


def get_trace_id() -> str:
    tid = trace_id_var.get()
    if tid is None:
        tid = generate_trace_id()
        trace_id_var.set(tid)
    return tid


def set_trace_id(trace_id: str) -> None:
    trace_id_var.set(trace_id)
