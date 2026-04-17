import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agents.research_graph import run_research
from backend.models.types import DEFAULT_CONFIG
from backend.agents.nodes.planner import PlannerOutput


@pytest.mark.asyncio
@patch("backend.agents.research_graph.plan_research")
@patch("backend.agents.research_graph.BranchProcessor")
@patch("backend.agents.research_graph.synthesize_answer")
async def test_run_research_returns_answer(mock_synth, mock_processor_class, mock_plan):
    from backend.models.types import BranchResult, Source

    mock_plan.return_value = PlannerOutput(
        sub_questions=["Q1?", "Q2?"],
        reasoning="Two branches needed.",
    )

    mock_instance = AsyncMock()
    mock_processor_class.return_value = mock_instance
    mock_instance.run.return_value = BranchResult(
        node_id="abc", question="Q1?", summary="S1", sources=[], depth=0, sub_branches=[],
    )
    mock_synth.return_value = "Final synthesized answer."

    queue: asyncio.Queue = asyncio.Queue()
    result = await run_research(
        job_id="job-1",
        query="What is X?",
        config=DEFAULT_CONFIG,
        event_queue=queue,
    )

    assert result["final_answer"] == "Final synthesized answer."
    assert len(result["branches"]) == 2


@pytest.mark.asyncio
@patch("backend.agents.research_graph.plan_research")
@patch("backend.agents.research_graph.BranchProcessor")
@patch("backend.agents.research_graph.synthesize_answer")
async def test_run_research_emits_research_started_and_complete(
    mock_synth, mock_processor_class, mock_plan
):
    from backend.models.types import BranchResult
    mock_plan.return_value = PlannerOutput(sub_questions=["Q1?"], reasoning="One branch.")
    mock_instance = AsyncMock()
    mock_processor_class.return_value = mock_instance
    mock_instance.run.return_value = BranchResult(
        node_id="abc", question="Q1?", summary="S", sources=[], depth=0, sub_branches=[],
    )
    mock_synth.return_value = "Answer."

    queue: asyncio.Queue = asyncio.Queue()
    await run_research("job-1", "Query", DEFAULT_CONFIG, queue)

    events = []
    while not queue.empty():
        events.append(await queue.get())

    event_types = [e["type"] for e in events if e is not None]
    assert "research_started" in event_types
    assert "plan_complete" in event_types
    assert "synthesis_started" in event_types
    assert "research_complete" in event_types


@pytest.mark.slow
@pytest.mark.asyncio
async def test_run_research_integration():
    """Integration test — requires real OPENAI_API_KEY and TAVILY_API_KEY."""
    from backend.config import settings
    queue: asyncio.Queue = asyncio.Queue()
    config = settings.research_config()
    config["max_branches"] = 2
    config["max_depth"] = 1

    result = await run_research(
        job_id="integration-test",
        query="What year was the Eiffel Tower built?",
        config=config,
        event_queue=queue,
    )

    assert result["final_answer"]
    assert len(result["branches"]) >= 1
