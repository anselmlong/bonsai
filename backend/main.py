import asyncio
import json
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


class ResearchRequest(BaseModel):
    query: str
    config: dict | None = None


class DiveDeeperRequest(BaseModel):
    node_id: str
    question: str


@app.post("/research")
async def start_research(req: ResearchRequest):
    job_id = uuid.uuid4().hex
    config: ResearchConfig = settings.research_config()
    if req.config:
        config.update(req.config)

    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"queue": queue, "result": None}

    async def _run():
        result = await run_research(job_id, req.query, config, queue)
        _jobs[job_id]["result"] = result

    asyncio.create_task(_run())
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
    if result is None:
        return {"status": "in_progress"}
    return {"status": "complete", **result}


@app.post("/research/{job_id}/dive-deeper")
async def dive_deeper(job_id: str, req: DiveDeeperRequest):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = _jobs[job_id]["queue"]
    config: ResearchConfig = settings.research_config()
    config["max_depth"] = 2  # always allow deeper

    async def _run_branch():
        from backend.agents.branch_processor import BranchProcessor
        processor = BranchProcessor(queue)
        await processor.run(
            question=req.question,
            parent_id=req.node_id,
            depth=1,
            config=config,
            parent_summary=None,
        )
        # Do NOT send sentinel — original stream stays open

    asyncio.create_task(_run_branch())
    return {"status": "spawned"}
