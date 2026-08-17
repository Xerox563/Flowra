# AgentFlow

A real SaaS-grade AI task runner. You give it a goal in plain English, it figures out a plan, searches the web, asks you before doing anything sketchy, then summarizes everything and hands you a polished report. Every single step hits your dashboard in real time with costs and timing.

---

## What This Is

AgentFlow is a working example of what production agentic systems actually look like. Not a notebook experiment. Not a toy. This is the kind of thing you'd run on real servers with real users hitting it.

It's intentionally small: just a Python FastAPI backend, a separate worker process for the heavy lifting, and a Next.js dashboard. But inside those three parts, you'll find the same patterns you see in production SaaS. Async job queues. Retry logic that actually works. State stored in Redis. Idempotent APIs. Every request gets a trace ID so you can debug later.

The whole thing scales horizontally. Throw more worker processes at the SQS queue and you handle more tasks. The API server is stateless. Run it on EC2 or Kubernetes — doesn't matter.

---

## Why This Matters

Running a GPT call in Jupyter is trivial. Running something 100 people can submit to at the same time, with retries that actually work, approval gates, proper error handling, and full visibility into what's happening? That's where things fall apart.

Here's what usually breaks:

- You hit submit twice by accident or your internet drops mid-upload. The same task runs twice. Double the tokens. Double the cost. **There's no idempotency check.**
- The agent is halfway through a task when something crashes. The state is corrupted. You don't know what happened. **There's no recovery.**
- The agent decides to call some external API without asking you first. It's doing stuff you didn't authorize. **You've lost control.**
- Something feels slow but you can't tell why. Which step? How many tokens? How much did this cost in USD? **There's no insight.**
- Traffic spikes. Everything hits the API server at once. It can't keep up. Everything times out and dies. **There's no backpressure.**
- A task fails. It's just gone. Lost forever. No way to retry it or figure out what went wrong. **There's no dead-letter queue.**
- Everyone logs things differently. `print()` in Python. `console.log()` in JavaScript. `grep` doesn't work. You can't build dashboards. **It's a mess.**

AgentFlow fixes all of this with nothing fancy. Just boring, proven infrastructure.

---

## How It Actually Works

### Stopping Duplicates

Every time you submit a goal, your request includes an `Idempotency-Key` header. It's a unique ID. The API checks Redis for that key before it does anything else. If it's there, it means you already submitted this exact thing. It just gives you back the task ID from before. No duplicate work. No double cost. This works even if you're on a flaky connection and hit submit three times.

### Jobs Don't Run Inside the API

The FastAPI server doesn't run the agent. It just creates a database row that says "task queued" and throws a message on an SQS queue. Then it immediately responds. Done. The actual work happens in a separate worker process that pulls jobs off the queue one at a time.

This matters because it means the API server never gets blocked. It can handle 10,000 requests per second while the workers chew through the heavy LLM calls in the background.

### What Happens When Something Breaks

The worker pulls a task off SQS. While it's working, that message is hidden from other workers (SQS calls this "visibility timeout"). If the worker finishes, it deletes the message. Job done.

But if something breaks — the worker crashes, or the process gets killed? The message becomes visible again. Another worker will pick it up and try again. By default, a message gets three attempts. If all three fail, SQS automatically moves it to a Dead Letter Queue. Someone can look at the DLQ later and figure out what went wrong without the bad messages clogging up the main queue.

### Asking Permission Before Acting

The agent has a step where it needs human approval. Before it does anything, it sets a Redis key that says "waiting for approval" and starts polling every two seconds.

Meanwhile, your dashboard sees this and pops up a modal. You can approve or reject. Click approve? Redis gets updated. The agent sees the change on its next poll and keeps going. The whole thing is super snappy because we're not making HTTP calls back and forth.

### Real-Time Dashboard Updates

When the worker completes a step, it writes an event to Redis and a row to the database. The frontend opens a Server-Sent Events connection — which is just the browser hanging on to an HTTP connection and waiting for the server to push data.

Every second, the API checks Redis for new events and sends them down. The dashboard updates instantly. You see the step turn green. You see how many tokens it used. You see how much it cost in USD. No polling. No refresh button. Just real time.

### Tracking Costs and Time

Every time the agent calls GPT-4o, we track how many input tokens, how many output tokens, and the latency. We do the math with the published OpenAI rates and calculate the USD cost. All of that goes into the database and also into structured JSON logs with a trace ID so you can connect the dots later.

At the end, you can see the total time, total tokens, and total cost for the entire task. And you can see the breakdown by step.

---

## What's Included

- The agent works like this: **plan out what to research**, **search for it on the web**, **pause for approval**, **summarize the results**, **write a final report**. Five steps.
- GPT-4o handles the planning, summarizing, and report writing. If the API key isn't set up, it uses stub responses so you can still test the UI locally.
- Web search uses Tavily. If something fails, it retries up to three times with backoff. Eventually gives up and moves on.
- Human approval is built in. The agent stops and asks before summarizing.
- Real-time updates. Everything flows to your dashboard as a stream. Keepalive pings every 15 seconds so the connection doesn't die.
- Data lives in Postgres. Every task, every step, every token count, every cost. All persisted.
- SQS handles the queue. DLQ handles failures. Visibility timeout is five minutes so workers have time to finish without getting their messages stolen.
- Redis backs everything. Idempotency keys, task state, approval flags, event streams.
- Double-clicking is safe. The idempotency check prevents duplicates.
- The API validates everything with Pydantic and FastAPI's request/response types.
- Database migrations are handled by Alembic.
- The dashboard is built with Next.js 14 App Router and Tailwind. Goal form on the home page. Live task view with timeline, approve button, and final report. Dashboard page with four KPI cards (total USD spent, tokens used, completed tasks, in-flight tasks) and a paginated history table.

---

## How It's Organized

```
agentflow/
├── frontend/                         # Next.js 14 App Router (TypeScript)
│   ├── app/
│   │   ├── layout.tsx                # Top nav + global Tailwind shell
│   │   ├── page.tsx                  # Goal input form (home /)
│   │   ├── tasks/[id]/page.tsx       # Live task view (SSE)
│   │   ├── dashboard/page.tsx        # History table + KPI cards
│   │   └── globals.css               # Tailwind directives
│   ├── components/
│   │   ├── GoalInput.tsx             # Textarea + examples + submit
│   │   ├── StepTimeline.tsx          # 5-step pipeline visualizer
│   │   ├── ApprovalModal.tsx         # Approve / reject dialog
│   │   └── CostBadge.tsx             # Tokens + USD micro pill
│   └── lib/
│       ├── api.ts                    # axios + typed interfaces + UUID idempotency
│       └── sse.ts                    # EventSource wrapper (listener pattern)
│
├── backend/                          # FastAPI (Python 3.11+)
│   ├── main.py                       # FastAPI init, CORS, router include
│   ├── routers/
│   │   ├── tasks.py                  # POST /tasks, GET /tasks, GET /tasks/{id}
│   │   ├── stream.py                 # GET /tasks/{id}/stream SSE endpoint
│   │   ├── approve.py                # POST /tasks/{id}/approve
│   │   └── health.py                 # GET /health, GET /ready
│   ├── services/
│   │   ├── queue.py                  # SQS publish / receive / delete / DLQ depth
│   │   ├── cache.py                  # Redis get / set / set_json / get_json
│   │   └── idempotency.py            # check_idempotency, store_idempotency
│   ├── worker/
│   │   ├── consumer.py               # SQS long-poll loop; delete on success only
│   │   ├── agent.py                  # LangGraph: plan/search/approval/summarize/synthesize
│   │   └── tools.py                  # Tavily search (tenacity 3× retry)
│   ├── models/
│   │   └── task.py                   # SQLAlchemy Task + TaskStep
│   ├── schemas/
│   │   └── task.py                   # Pydantic Request/Response schemas
│   ├── core/
│   │   ├── config.py                 # pydantic-settings env vars
│   │   ├── database.py               # SQLAlchemy engine / SessionLocal / get_db
│   │   ├── logging.py                # Structured JSON logger
│   │   └── tracing.py                # Per-request trace_id contextvar
│   ├── alembic/                      # Migrations
│   └── requirements.txt
│
└── infra/
    └── docker-compose.yml            # Local Postgres 15 + Redis 7
```

---

## The Technology Stack

| Layer             | Tech                                                            |
| ----------------- | --------------------------------------------------------------- |
| Frontend          | Next.js 14 (App Router) + Tailwind CSS + TypeScript             |
| Backend API       | FastAPI (Python 3.11+)                                          |
| Agent Engine      | LangGraph `StateGraph`                                          |
| LLM               | OpenAI GPT-4o via `langchain-openai`                            |
| Web Search        | Tavily API (3× retry, exponential backoff)                      |
| Async Queue       | AWS SQS (Main queue) + DLQ (max receives = 3, visibility 5 min) |
| Cache / State     | Redis (idempotency keys, task_state, approval, event stream)    |
| Database          | PostgreSQL 15 (SQLAlchemy ORM + Alembic migrations)             |
| Observability     | Structured JSON logs — trace_id, task_id, step on every line    |
| _(Phase 6)_ Auth  | JWT access + refresh tokens (python-jose / passlib-bcrypt)      |
| _(Phase 6)_ CI/CD | GitHub Actions → SSH deploy to AWS EC2 + RDS + ElastiCache      |

---
