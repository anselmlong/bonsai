from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict

NODE_EVENT_TYPES = {
    "research_started", "plan_complete", "branch_started",
    "branch_searching", "branch_reflecting", "branch_spawning",
    "branch_complete", "synthesis_started", "research_complete", "error",
}


class ResearchConfig(TypedDict, total=False):
    max_branches: int
    max_depth: int
    planner_model: str
    researcher_model: str
    synthesizer_model: str
    tavily_max_results: int


DEFAULT_CONFIG: ResearchConfig = ResearchConfig(
    max_branches=5,
    max_depth=2,
    planner_model="gpt-4o",
    researcher_model="gpt-4o-mini",
    synthesizer_model="gpt-4o",
    tavily_max_results=5,
)


class Source(TypedDict):
    url: str
    title: str
    excerpt: str
    score: float


class BranchResult(TypedDict):
    node_id: str
    question: str
    summary: str
    sources: list[Source]
    depth: int
    sub_branches: list


class NodeEvent(TypedDict):
    type: Literal[
        "research_started", "plan_complete",
        "branch_started", "branch_searching", "branch_reflecting",
        "branch_spawning", "branch_complete",
        "synthesis_started", "research_complete", "error",
    ]
    node_id: str
    parent_id: str | None
    depth: int
    question: str | None
    sources: list[Source] | None
    summary: str | None
    answer: str | None
    timestamp: float


class BranchProcessorInput(TypedDict):
    """Input sent to branch_runner node via LangGraph Send API."""
    job_id: str
    question: str
    depth: int
    parent_id: str | None
    parent_summary: str | None
    config: ResearchConfig


class ResearchState(TypedDict):
    job_id: str
    query: str
    config: ResearchConfig
    sub_questions: list[str]
    branches: Annotated[list[BranchResult], operator.add]
    final_answer: str
