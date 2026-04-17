from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from backend.models.types import ResearchConfig, Source

PROMPT = (Path(__file__).parent.parent / "prompts" / "reflect.md").read_text()


class ReflectOutput(BaseModel):
    should_recurse: bool
    sub_questions: list[str]
    summary: str


def reflect_on_results(
    question: str,
    sources: list[Source],
    depth: int,
    parent_summary: str | None,
    config: ResearchConfig,
) -> ReflectOutput:
    """Assess search results and decide whether to recurse. Skips LLM at max depth."""
    max_depth = config.get("max_depth", 2)
    max_branches = config.get("max_branches", 5)

    if depth >= max_depth:
        # No LLM call — build a minimal summary from source titles
        summary = ". ".join(s["title"] for s in sources[:3]) + "." if sources else ""
        return ReflectOutput(should_recurse=False, sub_questions=[], summary=summary)

    sources_text = "\n".join(
        f"- {s['title']}: {s['excerpt'][:200]}" for s in sources[:5]
    )
    llm = ChatOpenAI(model=config.get("researcher_model", "gpt-4o-mini"))
    structured = llm.with_structured_output(ReflectOutput)

    result: ReflectOutput = structured.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"""
Question: {question}
Current depth: {depth} / max depth: {max_depth}
Parent context: {parent_summary or "None"}

Search results:
{sources_text}
"""),
    ])

    result.sub_questions = result.sub_questions[:max_branches]
    return result
