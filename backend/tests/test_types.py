from backend.models.types import (
    Source, BranchResult, NodeEvent, BranchProcessorInput,
    ResearchState, ResearchConfig, DEFAULT_CONFIG,
)

def test_source_has_required_fields():
    s = Source(url="https://example.com", title="Example", excerpt="...", score=0.9)
    assert s["url"] == "https://example.com"
    assert s["score"] == 0.9

def test_node_event_types_are_valid():
    valid_types = {
        "research_started", "plan_complete", "branch_started",
        "branch_searching", "branch_reflecting", "branch_spawning",
        "branch_complete", "synthesis_started", "research_complete", "error",
    }
    from backend.models.types import NODE_EVENT_TYPES
    assert NODE_EVENT_TYPES == valid_types

def test_default_config_has_sensible_values():
    assert DEFAULT_CONFIG["max_branches"] == 5
    assert DEFAULT_CONFIG["max_depth"] == 2
    assert DEFAULT_CONFIG["tavily_max_results"] == 5
