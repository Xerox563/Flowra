import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

export function generateIdempotencyKey(): string {
  return crypto.randomUUID();
}

export interface TaskResponse {
  task_id: string;
  trace_id: string;
  status: string;
}

export interface TaskStepResponse {
  id: string;
  task_id: string;
  step_name: string;
  status: string;
  latency_ms?: number;
  tokens_used?: number;
  cost_usd?: number;
  output?: string;
  created_at: string;
}

export interface TaskDetailResponse {
  id: string;
  trace_id: string;
  goal: string;
  status: string;
  result?: string;
  total_tokens: number;
  total_cost_usd: number;
  created_at: string;
  updated_at: string;
  steps: TaskStepResponse[];
}

export interface StreamEvent {
  step: string;
  status: string;
  latency_ms?: number;
  tokens?: number;
  cost_usd?: number;
  message?: string;
  decision?: string;
  result?: string;
  type?: string;
  timestamp?: number;
}
