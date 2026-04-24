import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models.types import BranchResult, DEFAULT_CONFIG


async def test_run_research_returns_correct_shape():
    branch = BranchResult(
        node_id="abc123", question="Q1", summary="summary",
        sources=[], depth=0, sub_branches=[],
    )
    with (
        patch("experiment.plan_research") as mock_plan,
        patch("experiment.BranchProcessor") as mock_bp_class,
        patch("experiment.synthesize_answer", return_value="final answer"),
    ):
        mock_plan.return_value = MagicMock(sub_questions=["Q1"], reasoning="ok")
        mock_bp = MagicMock()
        mock_bp_class.return_value = mock_bp
        mock_bp.run = AsyncMock(return_value=branch)

        from experiment import run_research
        queue = asyncio.Queue()
        result = await run_research("job-1", "test query", DEFAULT_CONFIG, queue)

    assert "branches" in result
    assert "final_answer" in result
    assert result["final_answer"] == "final answer"
    assert len(result["branches"]) == 1
