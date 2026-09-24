import asyncio
import json
import logging
import time
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.agents.research_graph import run_research
from backend.config import settings
from backend.models.types import NodeEvent, ResearchConfig

app = FastAPI(title="Bonsai Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store: job_id → {queue, task, result}
_jobs: dict[str, dict] = {}
MAX_ACTIVE_JOBS = 2
MAX_RETAINED_JOBS = 100
logger = logging.getLogger(__name__)


class ResearchOverrides(BaseModel):
    """Only bounded workload options can be supplied by API clients."""
    model_config = ConfigDict(extra="forbid")
    max_branches: int | None = Field(default=None, ge=1, le=5)
    max_depth: int | None = Field(default=None, ge=0, le=2)
    tavily_max_results: int | None = Field(default=None, ge=1, le=10)
    synthesizer_max_sources: int | None = Field(default=None, ge=1, le=10)
    synthesizer_max_excerpt_chars: int | None = Field(default=None, ge=100, le=4000)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    config: ResearchOverrides | None = None


@app.post("/research")
async def start_research(req: ResearchRequest):
    if sum(job.get("status") == "running" for job in _jobs.values()) >= MAX_ACTIVE_JOBS:
        raise HTTPException(status_code=429, detail="Research capacity reached; retry when a job finishes")
    while len(_jobs) >= MAX_RETAINED_JOBS:
        completed = next((key for key, job in _jobs.items() if job.get("status") != "running"), None)
        if completed is None:
            raise HTTPException(status_code=429, detail="Research capacity reached")
        del _jobs[completed]
    # assign a unique job id to prevent collisions
    job_id = uuid.uuid4().hex
    config: ResearchConfig = settings.research_config()
    if req.config:
        config.update(req.config.model_dump(exclude_none=True))

    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"queue": queue, "result": None, "status": "running"}

    async def _run():
        try:
            result = await run_research(job_id, req.query, config, queue)
            _jobs[job_id].update(result=result, status="complete")
        except asyncio.CancelledError:
            _jobs[job_id]["status"] = "cancelled"
            raise
        except Exception:
            logger.exception("Research job %s failed", job_id)
            _jobs[job_id]["status"] = "failed"
            await queue.put(NodeEvent(
                type="error", node_id="root", parent_id=None, depth=0,
                question=None, sources=None, summary="Research failed; please try again",
                answer=None, timestamp=time.time(),
            ))
        finally:
            await queue.put(None)

    _jobs[job_id]["task"] = asyncio.create_task(_run())
    return {"job_id": job_id}


@app.get("/research/{job_id}/stream")
async def stream_research(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = _jobs[job_id]["queue"]

    async def event_generator() -> AsyncIterator[str]:
        while True:
            event = await queue.get()
            if event is None:  # sentinel
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/research/{job_id}/result")
async def get_result(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    result = _jobs[job_id].get("result")
    if _jobs[job_id].get("status") in {"failed", "cancelled"}:
        return {"status": _jobs[job_id]["status"]}
    if result is None:
        return {"status": "in_progress"}
    return {"status": "complete", **result}
