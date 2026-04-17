from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from backend.models.types import ResearchConfig

PROMPT = (Path(__file__).parent.parent / "prompts" / "planner.md").read_text()


class PlannerOutput(BaseModel):
    sub_questions: list[str]
    reasoning: str


def plan_research(query: str, config: ResearchConfig) -> PlannerOutput:
    """Decompose a query into sub-questions using the planner prompt."""
    max_branches = config.get("max_branches", 5)
    llm = ChatOpenAI(model=config.get("planner_model", "gpt-4o"))
    structured = llm.with_structured_output(PlannerOutput)

    result: PlannerOutput = structured.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"Research query: {query}\nMax sub-questions allowed: {max_branches}"),
    ])

    result.sub_questions = result.sub_questions[:max_branches]
    return result
