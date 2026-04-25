"""Autoresearch experiment file. The agent edits this file freely.

All prompts are inline strings. All pipeline logic is in one place.

Eval command:
    uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json
"""
import asyncio
import hashlib
import json
import logging
import time
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tavily import TavilyClient

from backend.models.types import BranchResult, NodeEvent, ResearchConfig, Source

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache" / "search"

# ── Prompts ───────────────────────────────────────────────────────────────────

PLANNER_PROMPT = """\
You are a research planner. Given a user query, decompose it into focused sub-questions that can be researched independently and in parallel.

## Scaling rules (follow exactly)
- Simple fact-finding (single answer, few entities): generate 1–2 sub-questions, expect 3–10 tool calls total.
- Comparisons or multi-part questions: generate 2–4 sub-questions, expect 10–15 tool calls each.
- Complex research (broad topic, multiple dimensions): generate 4–5 sub-questions with clearly divided responsibilities.

## Output
Return a JSON object with:
- `sub_questions`: array of strings (max length set by caller). Each sub-question is a complete, self-contained research question.
- `reasoning`: one sentence explaining your scaling decision.

## Rules
- Sub-questions must not overlap. Each should address a distinct dimension.
- Do not generate more sub-questions than the max allowed.
- Prefer depth over breadth within each sub-question.
"""

REFLECT_PROMPT = """\
You are a research quality assessor. Given a question and search results, decide whether the results are sufficient or whether deeper research is needed.

## Inputs
- The research question
- The current depth and maximum allowed depth
- The parent question context (if any)
- The search results found so far

## Output
Return a JSON object with:
- `should_recurse`: boolean — true only if results are incomplete AND depth < max_depth.
- `sub_questions`: array of strings — specific follow-up questions (only if should_recurse is true, else empty).
- `summary`: string — a concise synthesis of what was found in the search results, even if incomplete.

## Rules
- Only recurse if there are genuine gaps that sub-questions can fill.
- Do not recurse just because more information could theoretically exist.
- Sub-questions must be more specific than the parent question.
- Always produce a summary, even if sparse.
"""

SYNTHESIZER_PROMPT = """\
You are a research synthesizer. Given a user query and a complete set of research findings — organized as branches and sub-branches, each with a summary and full source excerpts — write a comprehensive, authoritative research article.

## Goal

Write a thorough, deeply researched article that demonstrates genuine expertise on the topic. The reader should feel they're getting a complete picture, not a superficial overview. Match the depth of a well-written Wikipedia long-form article or a proper explainer.

## Format

Use Markdown with `##` and `###` headings throughout. Structure:
- **Opening**: directly answer the query and state the key finding in a strong opening paragraph.
- **`##` sections**: one per major theme or branch. Use descriptive titles that reflect the topic, not the search question.
- **`###` sub-sections**: where sub-branches provide meaningful depth or nuance.
- **Closing `## Implications / Summary`**: synthesize across sections, note uncertainties, contradictions, or open questions.

## Citation rules

- Cite inline using `[Source Title](url)` after specific claims.
- Ground your writing in the provided source excerpts — but synthesize and expand upon them intelligently.
- If sources conflict, present both fairly and note the tension.

## Style rules

- Write as an expert explaining their knowledge, not a reporter summarizing documents.
- No meta-commentary about "our research" or "the branches show".
- Be thorough — don't be afraid to develop ideas across several paragraphs.
- Integrate sub-branch findings seamlessly within sections, not as separate bullet points.
- If source excerpts are rich with detail, draw on them fully. This is deep research — the reader expects comprehensiveness.
"""

# ── Search ────────────────────────────────────────────────────────────────────

def _cache_path(query: str, max_results: int) -> Path:
    key = hashlib.sha256(f"{query}{max_results}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def search(question: str, config: ResearchConfig) -> list[Source]:
    """Search Tavily with disk cache."""
    max_results = config.get("tavily_max_results", 5)
    path = _cache_path(question, max_results)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            return [Source(**r) for r in data["results"]]
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

    results: list[Source] = []
    try:
        client = TavilyClient()
        response = client.search(query=question, max_results=max_results, include_answer=False)
        results = [
            Source(
                url=r.get("url", ""),
                title=r.get("title", ""),
                excerpt=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in response.get("results", [])
        ]
    except Exception as e:
        logger.warning(f"Search failed: {e}")

    if results:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "query": question,
                "max_results": max_results,
                "results": [dict(r) for r in results],
            }))
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    return results


# ── Planner ───────────────────────────────────────────────────────────────────

class PlannerOutput(BaseModel):
    sub_questions: list[str]
    reasoning: str


def plan_research(query: str, config: ResearchConfig) -> PlannerOutput:
    max_branches = config.get("max_branches", 5)
    llm = ChatOpenAI(model=config.get("planner_model", "gpt-5.4-mini"), temperature=0)
    structured = llm.with_structured_output(PlannerOutput)
    result: PlannerOutput = structured.invoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Research query: {query}\nMax sub-questions allowed: {max_branches}"),
    ])
    result.sub_questions = result.sub_questions[:max_branches]
    return result


# ── Reflect ───────────────────────────────────────────────────────────────────

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
    max_depth = config.get("max_depth", 2)
    max_branches = config.get("max_branches", 5)

    if depth >= max_depth:
        summary = ". ".join(s["title"] for s in sources[:3]) + "." if sources else ""
        return ReflectOutput(should_recurse=False, sub_questions=[], summary=summary)

    sources_text = "\n".join(
        f"- {s['title']}: {s['excerpt'][:200]}" for s in sources[:5]
    )
    llm = ChatOpenAI(model=config.get("researcher_model", "gpt-4o"))
    structured = llm.with_structured_output(ReflectOutput)
    result: ReflectOutput = structured.invoke([
        SystemMessage(content=REFLECT_PROMPT),
        HumanMessage(content=f"""Question: {question}
Current depth: {depth} / max depth: {max_depth}
Parent context: {parent_summary or "None"}

Search results:
{sources_text}
"""),
    ])
    result.sub_questions = result.sub_questions[:max_branches]
    return result


# ── Synthesizer ───────────────────────────────────────────────────────────────

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


def synthesize_answer(query: str, branches: list[BranchResult], config: ResearchConfig) -> str:
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-5-mini-2025-08-07"))
    max_sources = config.get("synthesizer_max_sources", 4)
    max_excerpt_chars = config.get("synthesizer_max_excerpt_chars", None)
    branches_text = "\n\n".join(
        _flatten_branch(b, max_sources=max_sources, max_excerpt_chars=max_excerpt_chars)
        for b in branches
    )
    response = llm.invoke([
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"User query: {query}\n\nResearch findings:\n{branches_text}"),
    ])
    return response.content


# ── Branch Processor ──────────────────────────────────────────────────────────

class BranchProcessor:
    def __init__(self, event_queue: asyncio.Queue) -> None:
        self._queue = event_queue

    async def run(
        self,
        question: str,
        parent_id: str | None,
        depth: int,
        config: ResearchConfig,
        parent_summary: str | None,
    ) -> BranchResult:
        node_id = uuid.uuid4().hex[:8]
        max_depth = config.get("max_depth", 2)

        await self._emit(NodeEvent(
            type="branch_started", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))
        await self._emit(NodeEvent(
            type="branch_searching", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))
        sources = await asyncio.to_thread(search, question, config)

        await self._emit(NodeEvent(
            type="branch_reflecting", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))
        reflect = await asyncio.to_thread(
            reflect_on_results, question, sources, depth, parent_summary, config
        )

        sub_branches: list[BranchResult] = []
        if reflect.should_recurse and depth < max_depth and reflect.sub_questions:
            await self._emit(NodeEvent(
                type="branch_spawning", node_id=node_id, parent_id=parent_id,
                depth=depth, question=question, sources=None, summary=None,
                answer=None, timestamp=time.time(),
            ))
            tasks = [
                self.run(
                    question=q,
                    parent_id=node_id,
                    depth=depth + 1,
                    config=config,
                    parent_summary=reflect.summary,
                )
                for q in reflect.sub_questions
            ]
            sub_branches = list(await asyncio.gather(*tasks))

        await self._emit(NodeEvent(
            type="branch_complete", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=sources,
            summary=reflect.summary, answer=None, timestamp=time.time(),
        ))

        return BranchResult(
            node_id=node_id,
            question=question,
            summary=reflect.summary,
            sources=sources,
            depth=depth,
            sub_branches=sub_branches,
        )

    async def _emit(self, event: NodeEvent) -> None:
        await self._queue.put(event)


# ── Entry Point ───────────────────────────────────────────────────────────────

async def run_research(
    job_id: str,
    query: str,
    config: ResearchConfig,
    event_queue: asyncio.Queue,
) -> dict:
    processor = BranchProcessor(event_queue)

    await event_queue.put(NodeEvent(
        type="research_started", node_id="root", parent_id=None,
        depth=0, question=query, sources=None, summary=None,
        answer=None, timestamp=time.time(),
    ))

    plan = await asyncio.to_thread(plan_research, query, config)
    await event_queue.put(NodeEvent(
        type="plan_complete", node_id="planner", parent_id="root",
        depth=0, question=query, sources=None, summary=plan.reasoning,
        answer=None, timestamp=time.time(),
    ))

    tasks = [
        processor.run(
            question=q,
            parent_id="root",
            depth=0,
            config=config,
            parent_summary=None,
        )
        for q in plan.sub_questions
    ]
    branches: list[BranchResult] = list(await asyncio.gather(*tasks))

    await event_queue.put(NodeEvent(
        type="synthesis_started", node_id="synthesizer", parent_id="root",
        depth=0, question=query, sources=None, summary=None,
        answer=None, timestamp=time.time(),
    ))
    final_answer = await asyncio.to_thread(synthesize_answer, query, branches, config)

    await event_queue.put(NodeEvent(
        type="research_complete", node_id="root", parent_id=None,
        depth=0, question=query, sources=None, summary=None,
        answer=final_answer, timestamp=time.time(),
    ))

    return {"branches": branches, "final_answer": final_answer}
