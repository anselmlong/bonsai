from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.types import BranchResult, ResearchConfig

PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesizer.md").read_text()


def _flatten_branch(
    branch: BranchResult,
    depth: int = 0,
    max_sources: int = 4,
    max_excerpt_chars: int | None = None,
) -> str:
    indent = "  " * depth
    label = "Branch" if depth == 0 else "Sub-branch"
    lines = [
        f"{indent}{label}: {branch['question']}",
        f"{indent}Summary: {branch['summary']}",
    ]
    for s in branch["sources"][:max_sources]:
        excerpt = (
            s["excerpt"][:max_excerpt_chars].rstrip()
            if max_excerpt_chars
            else s["excerpt"].rstrip()
        )
        lines.append(f"{indent}Source — [{s['title']}]({s['url']}): {excerpt}")
    for child in branch.get("sub_branches", []):
        lines.append(_flatten_branch(child, depth + 1, max_sources, max_excerpt_chars))
    return "\n".join(lines)


def synthesize_answer(
    query: str,
    branches: list[BranchResult],
    config: ResearchConfig,
) -> str:
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-5-mini-2025-08-07"))
    max_sources = config.get("synthesizer_max_sources", 4)
    max_excerpt_chars = config.get("synthesizer_max_excerpt_chars", None)

    branches_text = "\n\n".join(
        _flatten_branch(b, max_sources=max_sources, max_excerpt_chars=max_excerpt_chars)
        for b in branches
    )

    response = llm.invoke(
        [
            SystemMessage(content=PROMPT),
            HumanMessage(
                content=f"User query: {query}\n\nResearch findings:\n{branches_text}"
            ),
        ]
    )
    return response.content
