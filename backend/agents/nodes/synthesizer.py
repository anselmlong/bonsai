from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.types import BranchResult, ResearchConfig

PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesizer.md").read_text()


def _flatten_branch(branch: BranchResult, depth: int = 0) -> str:
    indent = "  " * depth
    label = "Branch" if depth == 0 else "Sub-branch"
    lines = [
        f"{indent}{label}: {branch['question']}",
        f"{indent}Summary: {branch['summary']}",
    ]
    if branch["sources"]:
        lines.append(f"{indent}Sources: {', '.join(s['url'] for s in branch['sources'][:3])}")
    for child in branch.get("sub_branches", []):
        lines.append(_flatten_branch(child, depth + 1))
    return "\n".join(lines)


def synthesize_answer(
    query: str,
    branches: list[BranchResult],
    config: ResearchConfig,
) -> str:
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-4o"))

    branches_text = "\n\n".join(_flatten_branch(b) for b in branches)

    response = llm.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"User query: {query}\n\nResearch findings:\n{branches_text}"),
    ])
    return response.content
