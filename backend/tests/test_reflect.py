from unittest.mock import MagicMock, patch
from backend.agents.nodes.reflect import reflect_on_results, ReflectOutput
from backend.models.types import Source, DEFAULT_CONFIG


def _make_sources(n: int) -> list[Source]:
    return [
        Source(url=f"https://example.com/{i}", title=f"Source {i}", excerpt="Content.", score=0.9)
        for i in range(n)
    ]


@patch("backend.agents.nodes.reflect.ChatOpenAI")
def test_reflect_no_recurse_at_max_depth(mock_llm_class):
    config = {**DEFAULT_CONFIG, "max_depth": 2}
    result = reflect_on_results(
        question="What is climate change?",
        sources=_make_sources(5),
        depth=2,          # already at max
        parent_summary=None,
        config=config,
    )
    assert result.should_recurse is False
    assert result.sub_questions == []
    mock_llm_class.assert_not_called()   # skips LLM call entirely at max depth


@patch("backend.agents.nodes.reflect.ChatOpenAI")
def test_reflect_returns_structured_output(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value.with_structured_output.return_value = mock_llm
    mock_llm.invoke.return_value = ReflectOutput(
        should_recurse=True,
        sub_questions=["What are the main greenhouse gases?"],
        summary="Climate change is driven by human emissions.",
    )

    result = reflect_on_results(
        question="What causes climate change?",
        sources=_make_sources(3),
        depth=0,
        parent_summary=None,
        config=DEFAULT_CONFIG,
    )

    assert result.should_recurse is True
    assert len(result.sub_questions) == 1
    assert result.summary != ""


@patch("backend.agents.nodes.reflect.ChatOpenAI")
def test_reflect_caps_sub_questions_at_max_branches(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value.with_structured_output.return_value = mock_llm
    mock_llm.invoke.return_value = ReflectOutput(
        should_recurse=True,
        sub_questions=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"],  # 7 > max_branches=3
        summary="Summary.",
    )
    config = {**DEFAULT_CONFIG, "max_branches": 3}

    result = reflect_on_results(
        question="complex query",
        sources=_make_sources(3),
        depth=0,
        parent_summary=None,
        config=config,
    )

    assert len(result.sub_questions) <= 3
