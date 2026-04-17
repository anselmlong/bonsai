from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.types import BranchResult, ResearchConfig

PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesizer.md").read_text()


def synthesize_answer(
    query: str,
    branches: list[BranchResult],
    config: ResearchConfig,
) -> str:
    """Synthesize all branch results into a final answer."""
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-4o"))

    branches_text = "\n\n".join(
        f"### Branch: {b['question']}\n{b['summary']}\n"
        f"Sources: {', '.join(s['url'] for s in b['sources'][:3])}"
        for b in branches
    )

    response = llm.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"User query: {query}\n\nResearch branches:\n{branches_text}"),
    ])
    return response.content
