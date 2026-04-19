import asyncio
import time
from backend.models.types import (
    BranchResult, NodeEvent, ResearchConfig,
)
from backend.agents.nodes.planner import plan_research
from backend.agents.nodes.synthesizer import synthesize_answer
from backend.agents.branch_processor import BranchProcessor


async def run_research(
    job_id: str,
    query: str,
    config: ResearchConfig,
    event_queue: asyncio.Queue,
) -> dict:
    """Run the full research pipeline. Pushes NodeEvents to event_queue.

    Returns a dict with 'branches' and 'final_answer'.
    """
    processor = BranchProcessor(event_queue)

    # this is the starter node that starts the research.
    await event_queue.put(NodeEvent(
        type="research_started", node_id="root", parent_id=None,
        depth=0, question=query, sources=None, summary=None,
        answer=None, timestamp=time.time(),
    ))

    # Plan
    plan = await asyncio.to_thread(plan_research, query, config)
    await event_queue.put(NodeEvent(
        type="plan_complete", node_id="planner", parent_id="root",
        depth=0, question=query, sources=None, summary=plan.reasoning,
        answer=None, timestamp=time.time(),
    ))

    # Fan out branches in parallel
    tasks = [
        processor.run(
            question=q,
            parent_id="root",
            depth=0,
            config=config,
            parent_summary=None,
        )
        for q in plan.sub_questions
    ]
    branches: list[BranchResult] = list(await asyncio.gather(*tasks))

    # Synthesize
    await event_queue.put(NodeEvent(
        type="synthesis_started", node_id="synthesizer", parent_id="root",
        depth=0, question=query, sources=None, summary=None,
        answer=None, timestamp=time.time(),
    ))
    final_answer = await asyncio.to_thread(synthesize_answer, query, branches, config)

    await event_queue.put(NodeEvent(
        type="research_complete", node_id="root", parent_id=None,
        depth=0, question=query, sources=None, summary=None,
        answer=final_answer, timestamp=time.time(),
    ))

    return {"branches": branches, "final_answer": final_answer}
