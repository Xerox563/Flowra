from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id, set_trace_id
from backend.models.task import Task, TaskStep
from backend.services import cache
from backend.worker.tools import tavily_search

logger = get_logger(__name__)


GPT_COST_PER_INPUT_TOKEN = 5.0 / 1_000_000
GPT_COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000


class AgentState(TypedDict, total=False):
    task_id: str
    goal: str
    plan: list[str]
    search_results: list[dict[str, Any]]
    approved: bool
    summaries: list[str]
    final_report: str
    trace_id: str


def get_llm() -> ChatOpenAI:
    api_key = settings.OPENAI_API_KEY or "sk-stub"
    return ChatOpenAI(
        model="gpt-4o",
        api_key=api_key,
        temperature=0.2,
    )


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round(
        tokens_in * GPT_COST_PER_INPUT_TOKEN + tokens_out * GPT_COST_PER_OUTPUT_TOKEN,
        6,
    )


def _write_task_step(
    task_id: str,
    step_name: str,
    status: str,
    latency_ms: int | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
    output: str | None = None,
) -> None:
    try:
        db = SessionLocal()
        step = TaskStep(
            id=uuid.uuid4(),
            task_id=task_id,
            step_name=step_name,
            status=status,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            output=output,
        )
        db.add(step)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(
            "failed to write task step",
            extra={
                "task_id": task_id,
                "step": step_name,
                "error": str(e),
            },
        )


def _update_task_state(task_id: str, payload: dict[str, Any], ttl: int = 172800) -> None:
    cache.set_json(f"task_state:{task_id}", payload, ttl_seconds=ttl)


def _update_task_status(task_id: str, status: str, result: str | None = None, total_tokens: int = 0, total_cost_usd: float = 0.0) -> None:
    try:
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status
            if result is not None:
                task.result = result
            task.total_tokens = (task.total_tokens or 0) + total_tokens
            task.total_cost_usd = (task.total_cost_usd or 0.0) + total_cost_usd
            task.updated_at = db.func.now()
            db.commit()
        db.close()
    except Exception as e:
        logger.error(
            "failed to update task status",
            extra={"task_id": task_id, "status": status, "error": str(e)},
        )
    _update_task_state(
        task_id,
        {
            "status": status,
            "result": result,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
        },
    )


def _emit_step_event(task_id: str, step: str, status: str, **extra: Any) -> None:
    event = {"step": step, "status": status, **extra}
    existing = cache.get_json(f"task_events:{task_id}") or []
    existing.append(event)
    cache.set_json(f"task_events:{task_id}", existing, ttl_seconds=172800)
    _update_task_state(task_id, {"last_event": event})


def plan_node(state: AgentState) -> AgentState:
    task_id = state["task_id"]
    trace_id = state["trace_id"]
    set_trace_id(trace_id)
    start = time.time()

    step_name = "PLAN"
    logger.info(
        "plan node running",
        extra={"trace_id": trace_id, "task_id": task_id, "step": step_name, "status": "RUNNING"},
    )
    _write_task_step(task_id, step_name, "RUNNING")
    _emit_step_event(task_id, step_name, "RUNNING")
    _update_task_status(task_id, "RUNNING")

    goal = state["goal"]

    plan: list[str] = []
    tokens_in = 0
    tokens_out = 0

    if settings.OPENAI_API_KEY:
        try:
            llm = get_llm()
            prompt = (
                "Break the following user goal into 3 to 5 concrete sub-questions "
                "that can be answered via web search. Return ONLY a valid JSON array "
                "of strings, no other text.\n\nGoal:\n" + goal
            )
            resp = llm.invoke(prompt)
            content = resp.content or "[]"
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                tokens_in = int(resp.usage_metadata.get("input_tokens", 0))
                tokens_out = int(resp.usage_metadata.get("output_tokens", 0))
            try:
                plan = json.loads(content)
                if not isinstance(plan, list):
                    raise ValueError("not a list")
                plan = [str(p) for p in plan[:5]]
            except Exception:
                plan = [goal]
        except Exception as e:
            logger.error(
                "plan node LLM call failed falling back",
                extra={"trace_id": trace_id, "task_id": task_id, "error": str(e)},
            )
            plan = [goal]
    else:
        plan = [goal]

    if not plan:
        plan = [goal]

    latency_ms = int((time.time() - start) * 1000)
    cost = _estimate_cost(tokens_in, tokens_out)
    output_str = json.dumps(plan, ensure_ascii=False)

    logger.info(
        "plan node completed",
        extra={
            "trace_id": trace_id,
            "task_id": task_id,
            "step": step_name,
            "status": "COMPLETED",
            "latency_ms": latency_ms,
            "tokens_used": tokens_in + tokens_out,
            "cost_usd": cost,
        },
    )
    _write_task_step(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens_used=tokens_in + tokens_out,
        cost_usd=cost,
        output=output_str,
    )
    _emit_step_event(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens=tokens_in + tokens_out,
        cost_usd=cost,
    )
    _update_task_status(task_id, "RUNNING", total_tokens=tokens_in + tokens_out, total_cost_usd=cost)

    return {**state, "plan": plan}


def search_node(state: AgentState) -> AgentState:
    task_id = state["task_id"]
    trace_id = state["trace_id"]
    set_trace_id(trace_id)
    start = time.time()

    step_name = "SEARCH"
    logger.info(
        "search node running",
        extra={"trace_id": trace_id, "task_id": task_id, "step": step_name, "status": "RUNNING"},
    )
    _write_task_step(task_id, step_name, "RUNNING")
    _emit_step_event(task_id, step_name, "RUNNING")

    plan = state.get("plan", [state["goal"]])
    all_results: list[dict[str, Any]] = []

    for item in plan:
        try:
            results = tavily_search(item, max_results=3)
            for r in results:
                all_results.append({"query": item, **r})
        except Exception as e:
            logger.error(
                "search item failed continuing",
                extra={"trace_id": trace_id, "task_id": task_id, "query": item, "error": str(e)},
            )

    latency_ms = int((time.time() - start) * 1000)
    output_str = json.dumps(all_results[:20])[:50000]

    logger.info(
        "search node completed",
        extra={
            "trace_id": trace_id,
            "task_id": task_id,
            "step": step_name,
            "status": "COMPLETED",
            "latency_ms": latency_ms,
            "tokens_used": 0,
            "cost_usd": 0.0,
            "num_results": len(all_results),
        },
    )
    _write_task_step(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens_used=0,
        cost_usd=0.0,
        output=output_str,
    )
    _emit_step_event(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens=0,
        cost_usd=0.0,
    )

    return {**state, "search_results": all_results}


def approval_node(state: AgentState) -> AgentState:
    task_id = state["task_id"]
    trace_id = state["trace_id"]
    set_trace_id(trace_id)
    start = time.time()

    step_name = "APPROVAL"
    approval_key = f"approval:{task_id}"

    cache.set(approval_key, "PENDING", ttl_seconds=3600)
    _update_task_status(task_id, "AWAITING_APPROVAL")
    cache.set_json(f"task_state:{task_id}", {"status": "AWAITING_APPROVAL", "approval_pending": True}, ttl_seconds=172800)

    logger.info(
        "approval node waiting for decision",
        extra={"trace_id": trace_id, "task_id": task_id, "step": step_name, "status": "AWAITING_APPROVAL"},
    )
    _write_task_step(task_id, step_name, "RUNNING")
    _emit_step_event(
        task_id, step_name, "AWAITING_APPROVAL",
        message="Agent wants to access external URLs. Approve?",
    )

    approved = False
    timeout_s = 1800
    poll_s = 2
    waited = 0
    while waited < timeout_s:
        val = cache.get(approval_key)
        if val == "APPROVED":
            approved = True
            break
        if val == "REJECTED":
            approved = False
            break
        time.sleep(poll_s)
        waited += poll_s

    latency_ms = int((time.time() - start) * 1000)
    status_end = "COMPLETED" if approved else "FAILED"
    decision = "APPROVED" if approved else "REJECTED"

    logger.info(
        f"approval node {decision}",
        extra={
            "trace_id": trace_id,
            "task_id": task_id,
            "step": step_name,
            "status": status_end,
            "latency_ms": latency_ms,
        },
    )
    _write_task_step(
        task_id, step_name, status_end,
        latency_ms=latency_ms,
        tokens_used=0,
        cost_usd=0.0,
        output=decision,
    )
    _emit_step_event(
        task_id, step_name, status_end,
        latency_ms=latency_ms,
        decision=decision,
    )

    if approved:
        _update_task_status(task_id, "RUNNING")

    return {**state, "approved": approved}


def summarize_node(state: AgentState) -> AgentState:
    task_id = state["task_id"]
    trace_id = state["trace_id"]
    set_trace_id(trace_id)
    start = time.time()

    step_name = "SUMMARIZE"
    logger.info(
        "summarize node running",
        extra={"trace_id": trace_id, "task_id": task_id, "step": step_name, "status": "RUNNING"},
    )
    _write_task_step(task_id, step_name, "RUNNING")
    _emit_step_event(task_id, step_name, "RUNNING")

    search_results = state.get("search_results", [])
    summaries: list[str] = []
    total_in = 0
    total_out = 0

    if settings.OPENAI_API_KEY and search_results:
        llm = get_llm()
        for r in search_results[:10]:
            try:
                title = r.get("title", "")
                content = r.get("content", "")
                query = r.get("query", "")
                prompt = (
                    "Summarize the following web search result in 2 to 3 concise sentences, "
                    "focusing on information relevant to the query.\n\n"
                    f"Query: {query}\nTitle: {title}\nContent:\n{content[:3000]}"
                )
                resp = llm.invoke(prompt)
                summaries.append(str(resp.content) or "")
                if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                    total_in += int(resp.usage_metadata.get("input_tokens", 0))
                    total_out += int(resp.usage_metadata.get("output_tokens", 0))
            except Exception as e:
                logger.error(
                    "summarize item failed continuing",
                    extra={"trace_id": trace_id, "task_id": task_id, "error": str(e)},
                )
                summaries.append(r.get("content", "")[:500])
    else:
        for r in search_results:
            summaries.append(r.get("content", "")[:500])

    latency_ms = int((time.time() - start) * 1000)
    tokens = total_in + total_out
    cost = _estimate_cost(total_in, total_out)
    output_str = json.dumps(summaries, ensure_ascii=False)[:50000]

    logger.info(
        "summarize node completed",
        extra={
            "trace_id": trace_id,
            "task_id": task_id,
            "step": step_name,
            "status": "COMPLETED",
            "latency_ms": latency_ms,
            "tokens_used": tokens,
            "cost_usd": cost,
        },
    )
    _write_task_step(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens_used=tokens,
        cost_usd=cost,
        output=output_str,
    )
    _emit_step_event(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens=tokens,
        cost_usd=cost,
    )
    _update_task_status(task_id, "RUNNING", total_tokens=tokens, total_cost_usd=cost)

    return {**state, "summaries": summaries}


def synthesize_node(state: AgentState) -> AgentState:
    task_id = state["task_id"]
    trace_id = state["trace_id"]
    set_trace_id(trace_id)
    start = time.time()

    step_name = "SYNTHESIZE"
    logger.info(
        "synthesize node running",
        extra={"trace_id": trace_id, "task_id": task_id, "step": step_name, "status": "RUNNING"},
    )
    _write_task_step(task_id, step_name, "RUNNING")
    _emit_step_event(task_id, step_name, "RUNNING")

    goal = state["goal"]
    summaries = state.get("summaries", [])
    final_report = ""
    tokens_in = 0
    tokens_out = 0

    if settings.OPENAI_API_KEY:
        try:
            llm = get_llm()
            joined = "\n\n".join(f"- {s}" for s in summaries) or "(no results)"
            prompt = (
                "Using the following gathered summaries, write a coherent, well-structured "
                "final report that answers the user's goal. Include headings, clear structure, "
                "and cite key points. Aim for roughly 500 words minimum.\n\n"
                f"User goal: {goal}\n\nSummaries:\n{joined[:12000]}"
            )
            resp = llm.invoke(prompt)
            final_report = str(resp.content) or ""
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                tokens_in = int(resp.usage_metadata.get("input_tokens", 0))
                tokens_out = int(resp.usage_metadata.get("output_tokens", 0))
        except Exception as e:
            logger.error(
                "synthesize LLM failed falling back",
                extra={"trace_id": trace_id, "task_id": task_id, "error": str(e)},
            )
            final_report = "\n\n".join(summaries) if summaries else goal
    else:
        final_report = "\n\n".join(summaries) if summaries else goal

    latency_ms = int((time.time() - start) * 1000)
    tokens = tokens_in + tokens_out
    cost = _estimate_cost(tokens_in, tokens_out)

    logger.info(
        "synthesize node completed",
        extra={
            "trace_id": trace_id,
            "task_id": task_id,
            "step": step_name,
            "status": "COMPLETED",
            "latency_ms": latency_ms,
            "tokens_used": tokens,
            "cost_usd": cost,
        },
    )
    _write_task_step(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens_used=tokens,
        cost_usd=cost,
        output=final_report[:50000],
    )
    _emit_step_event(
        task_id, step_name, "COMPLETED",
        latency_ms=latency_ms,
        tokens=tokens,
        cost_usd=cost,
        result=final_report,
    )
    _update_task_status(
        task_id, "COMPLETED",
        result=final_report,
        total_tokens=tokens,
        total_cost_usd=cost,
    )

    return {**state, "final_report": final_report}


def approval_conditional(state: AgentState) -> Literal["summarize", "__end__"]:
    if state.get("approved"):
        return "summarize"
    return END


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("approval", approval_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "approval")
    graph.add_conditional_edges(
        "approval",
        approval_conditional,
        {"summarize": "summarize", END: END},
    )
    graph.add_edge("summarize", "synthesize")
    graph.add_edge("synthesize", END)

    return graph


COMPILED_GRAPH = None


def get_compiled_graph():
    global COMPILED_GRAPH
    if COMPILED_GRAPH is None:
        COMPILED_GRAPH = build_graph().compile()
    return COMPILED_GRAPH


def run_agent(task_id: str) -> None:
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.error("run_agent task not found", extra={"task_id": task_id})
        db.close()
        return
    goal = task.goal
    trace_id = task.trace_id or get_trace_id()
    db.close()

    set_trace_id(trace_id)
    logger.info(
        "run_agent starting",
        extra={"trace_id": trace_id, "task_id": task_id},
    )

    initial: AgentState = {
        "task_id": task_id,
        "goal": goal,
        "plan": [],
        "search_results": [],
        "approved": False,
        "summaries": [],
        "final_report": "",
        "trace_id": trace_id,
    }

    try:
        graph = get_compiled_graph()
        graph.invoke(initial)
    except Exception as e:
        logger.error(
            "run_agent failed marking task FAILED",
            extra={"trace_id": trace_id, "task_id": task_id, "error": str(e)},
        )
        _update_task_status(task_id, "FAILED")
        raise
