"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, generateIdempotencyKey } from "@/lib/api";

const EXAMPLES = [
  "Research impact of LLMs on SaaS pricing and write a 500-word report",
  "Summarize the top 5 AI product launches from last month",
  "Compare serverless databases and recommend one for a side project",
];

export function GoalInput() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || loading) return;

    setLoading(true);
    setError(null);

    const key = generateIdempotencyKey();
    try {
      const res = await api.post(
        "/tasks",
        { goal: goal.trim() },
        { headers: { "Idempotency-Key": key } }
      );
      router.push(`/tasks/${res.data.task_id}`);
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || "Failed to submit task. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 mb-3">
          Give AgentFlow a goal
        </h1>
        <p className="text-slate-600 text-lg">
          The agent will plan, search, and synthesize a report — with live streaming
          and human approval on external steps.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6"
      >
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Your goal
        </label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={5}
          placeholder="e.g. Research impact of LLMs on SaaS pricing and write a 500-word report"
          className="w-full rounded-lg border border-slate-300 p-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent resize-none"
          disabled={loading}
        />

        <div className="flex items-center justify-between mt-4">
          <div className="text-sm text-slate-500">
            Tip: be specific — include target audience, tone, and length.
          </div>
          <button
            type="submit"
            disabled={!goal.trim() || loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-sky-600 text-white font-medium shadow-sm hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Submitting…
              </>
            ) : (
              <>Submit →</>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}
      </form>

      <div className="mt-8">
        <p className="text-sm font-medium text-slate-500 mb-3">Or try an example:</p>
        <div className="grid gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setGoal(ex)}
              disabled={loading}
              className="text-left p-3 rounded-lg border border-slate-200 bg-white hover:border-sky-300 hover:bg-sky-50 text-sm text-slate-700 transition-colors disabled:opacity-50"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
