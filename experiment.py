"""Autoresearch experiment file. The agent edits this file freely.

All prompts are inline strings. All pipeline logic is in one place.

Eval command:
    uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json
"""
import asyncio
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

load_dotenv()  # ensures SERPER_API_KEY is available when running via uv

from backend.models.types import BranchResult, NodeEvent, ResearchConfig, Source

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache" / "search"

# ── Prompts ───────────────────────────────────────────────────────────────────

PLANNER_PROMPT = """\
You are a research planner. Given a user query — and optionally some initial web search results — decompose it into focused sub-questions for parallel research.

## Scaling rules (follow exactly)
- Simple fact-finding (single answer, few entities): generate 1–2 sub-questions.
- Comparisons or multi-part questions: generate 2–3 sub-questions.
- Complex research (broad topic, multiple dimensions): generate 3–5 sub-questions with clearly divided responsibilities.

## Output
Return a JSON object with:
- `sub_questions`: array of strings (max length set by caller). Each sub-question is complete and self-contained.
- `reasoning`: one sentence explaining your scaling decision.

## Rules
- Sub-questions must not overlap. Each must address a distinct dimension.
- Do not generate more sub-questions than the max allowed.
- Every sub-question must carry all named entities, proper nouns, years, and specific identifiers from the original query — do not drop person names, award names, event names, or numeric identifiers.
- If initial web results are provided, bias sub-questions toward filling gaps those results leave open, not repeating what they already cover.
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


def _search_serper(question: str, max_results: int) -> list[Source]:
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        return []
    response = httpx.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": question, "num": max_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return [
        Source(
            url=r.get("link", ""),
            title=r.get("title", ""),
            excerpt=r.get("snippet", ""),
            score=0.0,
        )
        for r in data.get("organic", [])[:max_results]
    ]


_brave_rate_lock = threading.Lock()
_brave_last_call_time: float = 0.0


def _search_brave(question: str, max_results: int) -> list[Source]:
    global _brave_last_call_time
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return []
    with _brave_rate_lock:
        elapsed = time.time() - _brave_last_call_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _brave_last_call_time = time.time()
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        params={"q": question, "count": max_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return [
        Source(
            url=r.get("url", ""),
            title=r.get("title", ""),
            excerpt=r.get("description", ""),
            score=0.0,
        )
        for r in data.get("web", {}).get("results", [])[:max_results]
    ]


def search(question: str, config: ResearchConfig) -> list[Source]:
    """Search with disk cache. Tries Serper first, falls back to Brave."""
    max_results = config.get("tavily_max_results", 5)
    path = _cache_path(question, max_results)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            return [Source(**r) for r in data["results"]]
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

    results: list[Source] = []
    for provider_fn, name in [(_search_serper, "Serper"), (_search_brave, "Brave")]:
        try:
            results = provider_fn(question, max_results)
            if results:
                break
        except Exception as e:
            logger.warning(f"{name} search failed: {e}")

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


def plan_research(
    query: str,
    config: ResearchConfig,
    initial_sources: list[Source] | None = None,
) -> PlannerOutput:
    max_branches = config.get("max_branches", 5)
    llm = ChatOpenAI(model=config.get("planner_model", "gpt-5.4-mini"), temperature=0)
    structured = llm.with_structured_output(PlannerOutput)

    initial_context = ""
    if initial_sources:
        lines = "\n".join(
            f"- {s['title']}: {s['excerpt'][:200]}" for s in initial_sources[:5]
        )
        initial_context = f"\n\nInitial web results for this query:\n{lines}"

    result: PlannerOutput = structured.invoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Research query: {query}\nMax sub-questions allowed: {max_branches}{initial_context}"),
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
    llm = ChatOpenAI(model=config.get("researcher_model", "gpt-4o"), temperature=0)
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
    # Recursion is disabled — initial search already informs the planner.
    # This caps searches at 1 (initial) + max_branches per question.
    result.should_recurse = False
    result.sub_questions = []
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
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-5-mini-2025-08-07"), temperature=0)
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

    initial_sources = await asyncio.to_thread(search, query, config)
    plan = await asyncio.to_thread(plan_research, query, config, initial_sources)
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
