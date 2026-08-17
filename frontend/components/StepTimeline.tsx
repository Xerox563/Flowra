"use client";

import { StreamEvent } from "@/lib/api";

const STEP_ORDER = ["PLAN", "SEARCH", "APPROVAL", "SUMMARIZE", "SYNTHESIZE"];

const STEP_LABEL: Record<string, string> = {
  PLAN: "Planning",
  SEARCH: "Web Search",
  APPROVAL: "Human Approval",
  SUMMARIZE: "Summarizing",
  SYNTHESIZE: "Final Report",
};

const STATUS_COLOR: Record<string, string> = {
  RUNNING: "bg-sky-500 border-sky-500",
  COMPLETED: "bg-emerald-500 border-emerald-500",
  AWAITING_APPROVAL: "bg-amber-500 border-amber-500",
  APPROVED: "bg-emerald-500 border-emerald-500",
  REJECTED: "bg-rose-500 border-rose-500",
  FAILED: "bg-rose-500 border-rose-500",
};

const STATUS_TEXT: Record<string, string> = {
  RUNNING: "Running…",
  COMPLETED: "Done",
  AWAITING_APPROVAL: "Waiting…",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  FAILED: "Failed",
};

interface Props {
  events: StreamEvent[];
}

export function StepTimeline({ events }: Props) {
  const latestByStep = new Map<string, StreamEvent>();
  for (const ev of events) {
    if (!ev.step) continue;
    latestByStep.set(ev.step, ev);
  }

  return (
    <ol className="relative border-l border-slate-200 ml-3">
      {STEP_ORDER.map((step, idx) => {
        const ev = latestByStep.get(step);
        const status = ev?.status || (ev ? ev.status : undefined);
        const dotColor = ev
          ? STATUS_COLOR[status!] || "bg-slate-300 border-slate-300"
          : "bg-white border-slate-300";

        return (
          <li key={step} className="ml-6 mb-6 last:mb-0">
            <span
              className={`absolute -left-[7px] mt-1.5 w-3.5 h-3.5 rounded-full border-2 ${dotColor} ${
                status === "RUNNING" ? "animate-pulse" : ""
              }`}
            />
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  {idx + 1}. {STEP_LABEL[step] || step}
                </h3>
                <div className="text-xs text-slate-500 mt-0.5">
                  {ev ? (
                    <>
                      {STATUS_TEXT[status!] || status}
                      {ev.latency_ms != null && status === "COMPLETED" && (
                        <> · {(ev.latency_ms / 1000).toFixed(1)}s</>
                      )}
                      {ev.tokens != null && (
                        <> · {ev.tokens.toLocaleString()} tokens</>
                      )}
                      {ev.cost_usd != null && ev.cost_usd > 0 && (
                        <> · ${ev.cost_usd.toFixed(5)}</>
                      )}
                    </>
                  ) : (
                    "Not started"
                  )}
                </div>
                {ev?.message && (
                  <p className="mt-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2">
                    {ev.message}
                  </p>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
