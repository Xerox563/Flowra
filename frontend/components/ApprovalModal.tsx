"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface Props {
  taskId: string;
  message?: string;
  onDecision: (decision: "APPROVED" | "REJECTED") => void;
}

export function ApprovalModal({ taskId, message, onDecision }: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function decide(decision: "approve" | "reject") {
    setBusy(true);
    setErr(null);
    try {
      await api.post(`/tasks/${taskId}/approve`, { decision });
      onDecision(decision === "approve" ? "APPROVED" : "REJECTED");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to submit decision");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 flex items-start gap-3">
          <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-amber-100 text-amber-700 font-bold shrink-0">
            !
          </span>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-900">
              Human Approval Required
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              {message ||
                "The agent wants to access external URLs to continue. Do you approve this step?"}
            </p>
          </div>
        </div>

        <div className="px-6 py-5 bg-slate-50 border-y border-slate-100">
          <p className="text-xs text-slate-500">
            If you approve, the agent will summarize all search results and
            synthesize a final report. If you reject, the task is marked as
            failed and no further work is performed.
          </p>
        </div>

        <div className="px-6 py-4 flex items-center justify-end gap-2">
          <button
            onClick={() => decide("reject")}
            disabled={busy}
            className="px-4 py-2 rounded-lg text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
          >
            Reject
          </button>
          <button
            onClick={() => decide("approve")}
            disabled={busy}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-sky-600 text-white hover:bg-sky-700 shadow-sm disabled:opacity-50"
          >
            {busy ? "Submitting…" : "Approve"}
          </button>
        </div>

        {err && (
          <div className="px-6 pb-4 text-sm text-rose-600">{err}</div>
        )}
      </div>
    </div>
  );
}
