from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health, tasks
from backend.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AgentFlow API",
    description="Production-grade AI task execution platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(tasks.router)


@app.on_event("startup")
def on_startup():
    logger.info("AgentFlow API starting up")


@app.on_event("shutdown")
def on_shutdown():
    logger.info("AgentFlow API shutting down")
