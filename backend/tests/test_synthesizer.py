from unittest.mock import MagicMock, patch
from backend.agents.nodes.synthesizer import synthesize_answer
from backend.models.types import BranchResult, Source, DEFAULT_CONFIG


def _make_branch(question: str, summary: str, sub_branches=None) -> BranchResult:
    return BranchResult(
        node_id="abc123",
        question=question,
        summary=summary,
        sources=[Source(url="https://example.com", title="Ex", excerpt="Exc.", score=0.9)],
        depth=1,
        sub_branches=sub_branches or [],
    )


@patch("backend.agents.nodes.synthesizer.ChatOpenAI")
def test_synthesize_answer_calls_llm_with_branches(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.invoke.return_value.content = "The final synthesized answer."

    branches = [
        _make_branch("What is Q1?", "Summary of Q1."),
        _make_branch("What is Q2?", "Summary of Q2."),
    ]

    answer = synthesize_answer("What is the topic?", branches, DEFAULT_CONFIG)

    assert answer == "The final synthesized answer."
    call_messages = mock_llm.invoke.call_args[0][0]
    # System message should contain prompt
    assert "synthesize" in call_messages[0].content.lower()
    # Human message should contain branch summaries
    assert "Summary of Q1" in call_messages[1].content
    assert "Summary of Q2" in call_messages[1].content


@patch("backend.agents.nodes.synthesizer.ChatOpenAI")
def test_synthesize_answer_uses_synthesizer_model(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.invoke.return_value.content = "Answer."
    config = {**DEFAULT_CONFIG, "synthesizer_model": "gpt-4o"}

    synthesize_answer("Query", [_make_branch("Q", "S")], config)

    mock_llm_class.assert_called_once_with(model="gpt-4o")


@patch("backend.agents.nodes.synthesizer.ChatOpenAI")
def test_synthesize_includes_sub_branch_summaries(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.invoke.return_value.content = "Article."

    child = BranchResult(
        node_id="child1", question="Sub-question?", summary="Deep finding.",
        sources=[], depth=1, sub_branches=[],
    )
    branch = BranchResult(
        node_id="abc123", question="Main?", summary="Top summary.",
        sources=[Source(url="https://example.com", title="Ex", excerpt=".", score=0.9)],
        depth=0, sub_branches=[child],
    )

    synthesize_answer("Query", [branch], DEFAULT_CONFIG)

    human_msg = mock_llm.invoke.call_args[0][0][1].content
    assert "Deep finding." in human_msg
    assert "Sub-question?" in human_msg
