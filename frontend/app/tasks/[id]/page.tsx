"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, StreamEvent, TaskDetailResponse } from "@/lib/api";
import { createSSEConnection } from "@/lib/sse";
import { StepTimeline } from "@/components/StepTimeline";
import { ApprovalModal } from "@/components/ApprovalModal";
import { CostBadge } from "@/components/CostBadge";

const STATUS_BADGE: Record<string, string> = {
  QUEUED: "bg-slate-100 text-slate-700",
  RUNNING: "bg-sky-100 text-sky-800",
  AWAITING_APPROVAL: "bg-amber-100 text-amber-800",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-rose-100 text-rose-800",
};

export default function TaskPage({ params }: { params: { id: string } }) {
  const taskId = params.id;
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [showApproval, setShowApproval] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    let closeSSE: (() => void) | null = null;

    async function fetchTask() {
      try {
        const res = await api.get(`/tasks/${taskId}`);
        if (cancel) return;
        const t = res.data as TaskDetailResponse;
        setTask(t);

        const initialEvents: StreamEvent[] = (t.steps || []).map((s) => ({
          step: s.step_name,
          status: s.status,
          latency_ms: s.latency_ms ?? undefined,
          tokens: s.tokens_used ?? undefined,
          cost_usd: s.cost_usd ?? undefined,
        }));
        setEvents(initialEvents);

        if (t.status === "AWAITING_APPROVAL") {
          setShowApproval(true);
        }
      } catch (e: any) {
        if (!cancel) setError(e?.response?.data?.detail || "Failed to load task");
      } finally {
        if (!cancel) setLoading(false);
      }
    }

    fetchTask();

    if (typeof window !== "undefined") {
      closeSSE = createSSEConnection(taskId, {
        onEvent: (ev) => {
          if (ev.type === "keepalive") return;
          setEvents((prev) => {
            const next = [...prev];
            if (
              ev.step &&
              (ev.status === "RUNNING" ||
                ev.status === "AWAITING_APPROVAL" ||
                ev.status === "COMPLETED" ||
                ev.status === "APPROVED" ||
                ev.status === "REJECTED" ||
                ev.status === "FAILED")
            ) {
              next.push(ev);
            }
            return next;
          });

          if (ev.step === "APPROVAL" && ev.status === "AWAITING_APPROVAL") {
            setShowApproval(true);
          }
          if (
            ev.step === "APPROVAL" &&
            (ev.status === "APPROVED" || ev.status === "REJECTED")
          ) {
            setShowApproval(false);
          }
        },
        onError: (e) => console.warn("SSE error", e),
      });
    }

    return () => {
      cancel = true;
      closeSSE?.();
    };
  }, [taskId]);

  const totals = useMemo(() => {
    let tokens = 0;
    let cost = 0;
    for (const ev of events) {
      if (ev.status === "COMPLETED") {
        tokens += ev.tokens ?? 0;
        cost += ev.cost_usd ?? 0;
      }
    }
    return { tokens, cost };
  }, [events]);

  const finalResult = useMemo(() => {
    const synth = [...events].reverse().find((e) => e.step === "SYNTHESIZE" && e.result);
    return synth?.result;
  }, [events]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-2/3" />
          <div className="h-4 bg-slate-200 rounded w-1/3" />
          <div className="h-64 bg-slate-200 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="max-w-xl mx-auto text-center py-20">
        <h2 className="text-2xl font-bold text-slate-900">Task not found</h2>
        <p className="text-slate-600 mt-2">{error || "Something went wrong."}</p>
        <Link
          href="/"
          className="inline-block mt-6 px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700"
        >
          ← Back to home
        </Link>
      </div>
    );
  }

  const statusClass = STATUS_BADGE[task.status] || STATUS_BADGE.QUEUED;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div className="min-w-0">
          <Link href="/" className="text-sm text-sky-700 hover:text-sky-800">
            ← New task
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 mt-2 break-words">
            {task.goal}
          </h1>
          <div className="flex items-center gap-3 mt-2 text-sm">
            <span className={`px-2.5 py-1 rounded-full font-medium ${statusClass}`}>
              {task.status}
            </span>
            <CostBadge tokens={totals.tokens} costUsd={totals.cost} />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-5">
              Progress
            </h2>
            <StepTimeline events={events} />
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                Final Report
              </h2>
            </div>
            {task.status === "QUEUED" && !finalResult ? (
              <div className="text-sm text-slate-500 italic">
                Task is queued. It will start processing shortly…
              </div>
            ) : finalResult ? (
              <article className="prose prose-slate max-w-none text-slate-800 whitespace-pre-wrap text-sm leading-relaxed">
                {finalResult}
              </article>
            ) : (
              <div className="text-sm text-slate-500 italic">
                Report will appear here once synthesis is complete.
              </div>
            )}
          </div>

          <div className="text-xs text-slate-500 flex gap-4">
            <span>
              Task ID: <code className="font-mono">{String(task.id).slice(0, 8)}…</code>
            </span>
            <span>
              Trace ID: <code className="font-mono">{String(task.trace_id).slice(0, 12)}…</code>
            </span>
          </div>
        </div>
      </div>

      {showApproval && (
        <ApprovalModal
          taskId={taskId}
          message={events.find((e) => e.step === "APPROVAL" && e.message)?.message}
          onDecision={() => setShowApproval(false)}
        />
      )}
    </div>
  );
}
