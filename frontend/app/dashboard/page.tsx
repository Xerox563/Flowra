"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, TaskListResponse } from "@/lib/api";

const STATUS_BADGE: Record<string, string> = {
  QUEUED: "bg-slate-100 text-slate-700",
  RUNNING: "bg-sky-100 text-sky-800",
  AWAITING_APPROVAL: "bg-amber-100 text-amber-800",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-rose-100 text-rose-800",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString();
}

function truncate(s: string, n = 80) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export default function DashboardPage() {
  const [data, setData] = useState<TaskListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancel = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await api.get("/tasks", { params: { page, per_page: 20 } });
        if (!cancel) setData(r.data as TaskListResponse);
      } catch (e: any) {
        if (!cancel) setError(e?.response?.data?.detail || "Failed to load tasks");
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [page]);

  const summary = useMemo(() => {
    const items = data?.items || [];
    const total = items.reduce((a, b) => a + (b.total_cost_usd || 0), 0);
    const tokens = items.reduce((a, b) => a + (b.total_tokens || 0), 0);
    const completed = items.filter((i) => i.status === "COMPLETED").length;
    const failed = items.filter((i) => i.status === "FAILED").length;
    const running = items.filter(
      (i) => i.status === "RUNNING" || i.status === "AWAITING_APPROVAL" || i.status === "QUEUED"
    ).length;
    return { total, tokens, completed, failed, running, items };
  }, [data]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-600 mt-1">History of all tasks and aggregate cost.</p>
        </div>
        <Link
          href="/"
          className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 text-sm font-medium"
        >
          + New task
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-4 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Total cost
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-700">
            ${summary.total.toFixed(5)}
          </div>
          <div className="text-xs text-slate-500 mt-1">across loaded page</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Total tokens
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {summary.tokens.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 mt-1">GPT-4o (input + output)</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Completed
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-700">{summary.completed}</div>
          <div className="text-xs text-slate-500 mt-1">successful tasks</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            In flight
          </div>
          <div className="mt-2 text-2xl font-bold text-sky-700">{summary.running}</div>
          <div className="text-xs text-slate-500 mt-1">{summary.failed} failed</div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left font-semibold text-slate-600 px-5 py-3">Goal</th>
                <th className="text-left font-semibold text-slate-600 px-5 py-3">Status</th>
                <th className="text-right font-semibold text-slate-600 px-5 py-3">Tokens</th>
                <th className="text-right font-semibold text-slate-600 px-5 py-3">Cost</th>
                <th className="text-left font-semibold text-slate-600 px-5 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                    Loading tasks…
                  </td>
                </tr>
              )}
              {!loading && error && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-rose-600">
                    {error}
                  </td>
                </tr>
              )}
              {!loading && !error && summary.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-16 text-center text-slate-500">
                    No tasks yet.{" "}
                    <Link href="/" className="text-sky-700 hover:text-sky-800 font-medium">
                      Create your first task →
                    </Link>
                  </td>
                </tr>
              )}
              {!loading && !error && summary.items.map((t) => (
                <tr
                  key={String(t.id)}
                  className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60"
                >
                  <td className="px-5 py-3">
                    <Link
                      href={`/tasks/${t.id}`}
                      className="text-slate-900 hover:text-sky-700 font-medium block"
                    >
                      {truncate(t.goal, 90)}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        STATUS_BADGE[t.status] || STATUS_BADGE.QUEUED
                      }`}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-slate-700">
                    {(t.total_tokens || 0).toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums text-emerald-700 font-medium">
                    ${(t.total_cost_usd || 0).toFixed(5)}
                  </td>
                  <td className="px-5 py-3 text-slate-600 text-xs">
                    {formatDate(t.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {data && data.total > data.per_page && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 bg-slate-50/60 text-sm">
            <div className="text-slate-600">
              Showing {Math.min(data.total, (data.page - 1) * data.per_page + 1)}-
              {Math.min(data.total, data.page * data.per_page)} of {data.total}
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-50 hover:bg-slate-50"
              >
                Prev
              </button>
              <span className="text-slate-600">
                Page {data.page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-md border border-slate-200 bg-white text-slate-700 disabled:opacity-50 hover:bg-slate-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
