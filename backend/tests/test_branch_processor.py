import asyncio
import pytest
from unittest.mock import MagicMock, patch
from backend.agents.branch_processor import BranchProcessor
from backend.models.types import DEFAULT_CONFIG, Source, BranchResult
from backend.agents.nodes.reflect import ReflectOutput


def _make_sources() -> list[Source]:
    return [Source(url="https://example.com", title="Ex", excerpt="Exc.", score=0.9)]


async def _drain_queue(q: asyncio.Queue) -> list:
    events = []
    while not q.empty():
        events.append(await q.get())
    return events


@pytest.mark.asyncio
@patch("backend.agents.branch_processor.search_tavily")
@patch("backend.agents.branch_processor.reflect_on_results")
async def test_branch_processor_emits_events(mock_reflect, mock_search):
    mock_search.return_value = _make_sources()
    mock_reflect.return_value = ReflectOutput(
        should_recurse=False, sub_questions=[], summary="Found relevant info."
    )

    queue: asyncio.Queue = asyncio.Queue()
    processor = BranchProcessor(queue)
    result = await processor.run(
        question="What is X?",
        parent_id=None,
        depth=0,
        config=DEFAULT_CONFIG,
        parent_summary=None,
    )

    events = await _drain_queue(queue)
    event_types = [e["type"] for e in events]

    assert "branch_started" in event_types
    assert "branch_searching" in event_types
    assert "branch_reflecting" in event_types
    assert "branch_complete" in event_types
    assert isinstance(result, dict)
    assert result["question"] == "What is X?"
    assert result["depth"] == 0
    assert len(result["sources"]) == 1


@pytest.mark.asyncio
@patch("backend.agents.branch_processor.search_tavily")
@patch("backend.agents.branch_processor.reflect_on_results")
async def test_branch_processor_recurses_when_reflect_says_so(mock_reflect, mock_search):
    call_count = {"n": 0}

    def reflect_side_effect(question, sources, depth, parent_summary, config):
        call_count["n"] += 1
        if depth == 0:
            return ReflectOutput(
                should_recurse=True,
                sub_questions=["Sub-question A?"],
                summary="Top-level summary.",
            )
        return ReflectOutput(should_recurse=False, sub_questions=[], summary="Deep summary.")

    mock_search.return_value = _make_sources()
    mock_reflect.side_effect = reflect_side_effect

    queue: asyncio.Queue = asyncio.Queue()
    processor = BranchProcessor(queue)
    result = await processor.run(
        question="Top question?",
        parent_id=None,
        depth=0,
        config={**DEFAULT_CONFIG, "max_depth": 2},
        parent_summary=None,
    )

    # Reflect should have been called twice: once at depth 0, once at depth 1
    assert call_count["n"] == 2
    assert len(result["sub_branches"]) == 1


@pytest.mark.asyncio
@patch("backend.agents.branch_processor.search_tavily")
@patch("backend.agents.branch_processor.reflect_on_results")
async def test_branch_processor_does_not_recurse_beyond_max_depth(mock_reflect, mock_search):
    mock_search.return_value = _make_sources()
    # reflect always wants to recurse — but depth cap should stop it
    mock_reflect.return_value = ReflectOutput(
        should_recurse=True,
        sub_questions=["Sub?"],
        summary="Summary.",
    )

    queue: asyncio.Queue = asyncio.Queue()
    processor = BranchProcessor(queue)
    result = await processor.run(
        question="Question?",
        parent_id=None,
        depth=2,   # already at max
        config={**DEFAULT_CONFIG, "max_depth": 2},
        parent_summary=None,
    )

    # At max depth, reflect is skipped entirely — no sub_branches
    assert result["sub_branches"] == []
