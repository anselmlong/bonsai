from unittest.mock import MagicMock, patch
from backend.agents.nodes.planner import plan_research, PlannerOutput
from backend.models.types import DEFAULT_CONFIG


@patch("backend.agents.nodes.planner.ChatOpenAI")
def test_plan_research_returns_sub_questions(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value.with_structured_output.return_value = mock_llm
    mock_llm.invoke.return_value = PlannerOutput(
        sub_questions=["Q1?", "Q2?", "Q3?"],
        reasoning="Complex query requiring 3 branches.",
    )

    result = plan_research("What are the effects of remote work?", DEFAULT_CONFIG)

    assert result.sub_questions == ["Q1?", "Q2?", "Q3?"]
    assert result.reasoning != ""


@patch("backend.agents.nodes.planner.ChatOpenAI")
def test_plan_research_caps_at_max_branches(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value.with_structured_output.return_value = mock_llm
    mock_llm.invoke.return_value = PlannerOutput(
        sub_questions=["Q1?", "Q2?", "Q3?", "Q4?", "Q5?", "Q6?"],  # 6 returned
        reasoning="Many branches.",
    )
    config = {**DEFAULT_CONFIG, "max_branches": 3}

    result = plan_research("Complex query", config)

    assert len(result.sub_questions) <= 3


@patch("backend.agents.nodes.planner.ChatOpenAI")
def test_plan_research_uses_planner_model(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value.with_structured_output.return_value = mock_llm
    mock_llm.invoke.return_value = PlannerOutput(sub_questions=["Q?"], reasoning="Simple.")
    config = {**DEFAULT_CONFIG, "planner_model": "gpt-4o"}

    plan_research("query", config)

    mock_llm_class.assert_called_once_with(model="gpt-4o")
