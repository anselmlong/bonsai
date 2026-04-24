# Autoresearch Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the autoresearch loop — a self-contained `experiment.py` the agent edits freely, an `--experiment` flag on `eval.py` with a weighted composite metric, and a `program.md` that guides the agent.

**Architecture:** `experiment.py` is a repo-root copy of the full research pipeline with all prompts as inline strings. `eval.py` gets an `--experiment` flag that swaps `run_research` to the experiment version and reports a weighted composite score. `program.md` documents research directions and the eval workflow for the agent.

**Tech Stack:** Python asyncio, langchain-openai, tavily-python, pydantic, pytest-asyncio (asyncio_mode=auto)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `experiment.py` | Create | Self-contained pipeline the agent edits freely — prompts inline, all logic in one file |
| `scripts/eval.py` | Modify | Add `--experiment` flag, `WEIGHTS`, `composite_score`, conditional import |
| `backend/tests/test_eval_composite.py` | Create | Unit tests for `composite_score` |
| `backend/tests/test_experiment.py` | Create | Shape test for `experiment.run_research` |
| `program.md` | Create | Research directions and workflow for the autoresearch agent |

---

### Task 1: Create `experiment.py` as self-contained pipeline copy

**Files:**
- Create: `experiment.py`
- Create: `backend/tests/test_experiment.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_experiment.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models.types import BranchResult, DEFAULT_CONFIG


async def test_run_research_returns_correct_shape():
    branch = BranchResult(
        node_id="abc123", question="Q1", summary="summary",
        sources=[], depth=0, sub_branches=[],
    )
    with (
        patch("experiment.plan_research") as mock_plan,
        patch("experiment.BranchProcessor") as mock_bp_class,
        patch("experiment.synthesize_answer", return_value="final answer"),
    ):
        mock_plan.return_value = MagicMock(sub_questions=["Q1"], reasoning="ok")
        mock_bp = MagicMock()
        mock_bp_class.return_value = mock_bp
        mock_bp.run = AsyncMock(return_value=branch)

        from experiment import run_research
        queue = asyncio.Queue()
        result = await run_research("job-1", "test query", DEFAULT_CONFIG, queue)

    assert "branches" in result
    assert "final_answer" in result
    assert result["final_answer"] == "final answer"
    assert len(result["branches"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_experiment.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'experiment'`

- [ ] **Step 3: Create `experiment.py`**

Create `/home/anselmlong/Projects/bonsai/experiment.py` with the full content below.
The file is a direct copy of the pipeline with prompts inlined. Do not alter logic — copy exactly.

```python
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
    llm = ChatOpenAI(model=config.get("planner_model", "gpt-5.4-mini"))
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_experiment.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add experiment.py backend/tests/test_experiment.py
git commit -m "feat: add experiment.py — self-contained pipeline for autoresearch"
```

---

### Task 2: Add `--experiment` flag and composite score to `eval.py`

**Files:**
- Modify: `scripts/eval.py`
- Create: `backend/tests/test_eval_composite.py`

- [ ] **Step 1: Create `scripts/__init__.py` so `scripts` is importable as a package**

```bash
touch /home/anselmlong/Projects/bonsai/scripts/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_eval_composite.py`:

```python
from scripts.eval import composite_score, WEIGHTS


def test_composite_score_all_ones():
    scores = {d: 1.0 for d in WEIGHTS}
    assert abs(composite_score(scores) - 1.0) < 1e-9


def test_composite_score_all_zeros():
    scores = {d: 0.0 for d in WEIGHTS}
    assert composite_score(scores) == 0.0


def test_composite_score_only_factual():
    scores = {d: 0.0 for d in WEIGHTS}
    scores["factual_accuracy"] = 1.0
    assert abs(composite_score(scores) - 0.50) < 1e-9


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_eval_composite.py -v
```

Expected: FAIL with `ImportError: cannot import name 'composite_score' from 'scripts.eval'`

- [ ] **Step 4: Add `WEIGHTS`, `composite_score`, `--experiment` flag, and conditional import to `eval.py`**

Replace the top of `scripts/eval.py` — the imports and constants section — with:

```python
#!/usr/bin/env python3
"""SimpleQA evaluation harness for Bonsai.

Usage:
    python scripts/eval.py --n 50 --output results/eval.json
    python scripts/eval.py --n 20 --output results/experiment.json --experiment

Requirements:
    - OPENAI_API_KEY and TAVILY_API_KEY set in environment
    - Backend dependencies installed (pip install -e .)
    - SimpleQA dataset downloaded from HuggingFace (auto-downloaded on first run)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset
from openai import OpenAI

from backend.config import settings
from backend.models.types import DEFAULT_CONFIG

JUDGE_PROMPT = """You are evaluating the quality of an AI research answer against a known correct answer.

Question: {question}
Correct answer: {gold}
AI answer: {answer}

Score each dimension from 0.0 to 1.0:
- factual_accuracy: Does the answer contain the correct facts? (1.0 = fully correct, 0.0 = wrong)
- citation_accuracy: Are the sources real, relevant, and properly cited?
- completeness: Does it address all aspects of the question?
- source_quality: Are sources authoritative (academic, news, official) vs low-quality SEO?
- conciseness: Is the answer direct without unnecessary padding?

Return JSON only: {{"factual_accuracy": 0.0, "citation_accuracy": 0.0, "completeness": 0.0, "source_quality": 0.0, "conciseness": 0.0}}"""

DIMENSIONS = ["factual_accuracy", "citation_accuracy", "completeness", "source_quality", "conciseness"]

WEIGHTS: dict[str, float] = {
    "factual_accuracy": 0.50,
    "completeness": 0.20,
    "citation_accuracy": 0.20,
    "source_quality": 0.05,
    "conciseness": 0.05,
}


def composite_score(scores: dict[str, float]) -> float:
    return sum(scores.get(dim, 0.0) * weight for dim, weight in WEIGHTS.items())
```

Then update `evaluate_question` to accept `run_research_fn` as a parameter instead of importing at module level:

```python
async def evaluate_question(
    question: str,
    gold_answer: str,
    config: dict,
    oai_client: OpenAI,
    run_research_fn,
) -> EvalResult:
    queue: asyncio.Queue = asyncio.Queue()
    start = time.time()
    try:
        result = await run_research_fn(
            job_id=f"eval-{int(start)}",
            query=question,
            config=config,
            event_queue=queue,
        )
        latency = time.time() - start
        answer = result["final_answer"]
        branch_count = len(result["branches"])
        source_count = sum(len(b["sources"]) for b in result["branches"])
        scores = grade_answer(oai_client, question, gold_answer, answer)
        return EvalResult(
            question=question,
            gold_answer=gold_answer,
            agent_answer=answer,
            latency_s=round(latency, 2),
            branch_count=branch_count,
            source_count=source_count,
            scores=scores,
            error=None,
        )
    except Exception as e:
        return EvalResult(
            question=question, gold_answer=gold_answer, agent_answer="",
            latency_s=round(time.time() - start, 2), branch_count=0, source_count=0,
            scores={d: 0.0 for d in DIMENSIONS}, error=str(e),
        )
```

Then update `main` to resolve `run_research` based on `--experiment` and pass it through:

```python
async def main(n: int, output_path: str, concurrency: int, experiment: bool) -> None:
    if experiment:
        from experiment import run_research as run_research_fn
        print("Using experiment.py pipeline")
    else:
        from backend.agents.research_graph import run_research as run_research_fn

    print(f"Loading SimpleQA dataset (first {n} questions)…")
    ds = load_dataset("basicv8vc/SimpleQA", split="test")
    samples = list(ds.select(range(n)))

    config = settings.research_config()
    config["max_branches"] = 3
    config["max_depth"] = 1

    oai_client = OpenAI(api_key=settings.openai_api_key)
    results: list[EvalResult] = []
    sem = asyncio.Semaphore(concurrency)

    async def run_with_sem(s):
        async with sem:
            r = await evaluate_question(s["problem"], s["answer"], config, oai_client, run_research_fn)
            cs = composite_score(r["scores"])
            print(f"  {'✓' if r['scores']['factual_accuracy'] >= 0.7 else '✗'} [{cs:.2f}] {s['problem'][:55]}")
            return r

    print(f"Running {n} questions (concurrency={concurrency})…")
    results = await asyncio.gather(*[run_with_sem(s) for s in samples])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    valid = [r for r in results if not r["error"]]
    correct = [r for r in valid if r["scores"]["factual_accuracy"] >= 0.7]
    avg_scores = {
        dim: sum(r["scores"][dim] for r in valid) / len(valid)
        for dim in DIMENSIONS
    } if valid else {}
    avg_composite = sum(composite_score(r["scores"]) for r in valid) / len(valid) if valid else 0.0
    avg_latency = sum(r["latency_s"] for r in valid) / len(valid) if valid else 0
    avg_sources = sum(r["source_count"] for r in valid) / len(valid) if valid else 0

    print(f"""
─────────────────────────────────────
SimpleQA Eval — bonsai
Questions:        {n}
Errors:           {len(results) - len(valid)}
Correct (≥0.7):   {len(correct)}  ({100*len(correct)/n:.1f}%)
Composite score:  {avg_composite:.3f}
Avg latency:      {avg_latency:.1f}s
Avg sources:      {avg_sources:.1f}
─────────────────────────────────────
Dimension scores:""")
    for dim, score in avg_scores.items():
        weight = WEIGHTS[dim]
        print(f"  {dim:<22} {score:.2f}  (weight {weight:.2f})")
    print(f"─────────────────────────────────────")
    print(f"Results written to {output_path}")
```

Finally update the `argparse` block at the bottom:

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Number of questions to evaluate")
    parser.add_argument("--output", type=str, default="results/eval.json", help="Output JSONL path")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel requests")
    parser.add_argument("--experiment", action="store_true", help="Use experiment.py instead of research_graph.py")
    args = parser.parse_args()
    asyncio.run(main(args.n, args.output, args.concurrency, args.experiment))
```

- [ ] **Step 5: Run composite score tests**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_eval_composite.py -v
```

Expected: all 4 PASS

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/ -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/__init__.py scripts/eval.py backend/tests/test_eval_composite.py
git commit -m "feat: add --experiment flag and weighted composite score to eval.py"
```

---

### Task 3: Create `program.md`

**Files:**
- Create: `program.md`

No automated test — this is a guidance document for the autoresearch agent.

- [ ] **Step 1: Create `program.md` at repo root**

```markdown
# Bonsai Autoresearch Program

## What You're Optimizing

You are improving `experiment.py`, a self-contained research agent pipeline that answers
factual questions. Edit this file to improve the composite score on SimpleQA.

**Eval command:**
    uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json

**Metric:** weighted composite score (higher is better)
- factual_accuracy  × 0.50
- completeness      × 0.20
- citation_accuracy × 0.20
- source_quality    × 0.05
- conciseness       × 0.05

**Baseline composite score:** TBD — run eval once before starting experiments

## Current Architecture

```
query
  → plan_research()     — LLM decomposes into sub-questions (PLANNER_PROMPT)
  → BranchProcessor     — each sub-question fans out in parallel:
      → search()        — Tavily web search (disk-cached)
      → reflect_on_results()  — LLM decides quality / whether to recurse (REFLECT_PROMPT)
      → [recursive sub-branches if needed]
  → synthesize_answer() — LLM combines all branches into final answer (SYNTHESIZER_PROMPT)
```

All prompts (`PLANNER_PROMPT`, `REFLECT_PROMPT`, `SYNTHESIZER_PROMPT`) are inline strings.
All logic is in this one file. Edit freely.

## Research Directions

### Primary: Search Before Planning

**Hypothesis:** The planner currently operates blind — it sees only the raw query, no web
content. If we run an initial `search(query, config)` first and pass those results to
`plan_research`, the planner can generate better-targeted sub-questions grounded in
what's actually on the web.

**What to try:**
1. In `run_research`, call `search(query, config)` before `plan_research`
2. Pass the search results as additional context in the `HumanMessage` inside `plan_research`
3. Update `PLANNER_PROMPT` to instruct the planner to use the initial search context

**Expected benefit:** Fewer redundant sub-questions, better coverage of what's actually
findable, higher factual accuracy and completeness.

### Secondary: Planner Prompt Tuning

- Try stricter scaling rules: bias toward 1 sub-question for simple fact queries
- Require sub-questions to mention key named entities from the original query
- Add a "what is still unknown after a quick web search?" framing

### Secondary: Reflect Conservatism

- Default recurses when there are "genuine gaps" — try raising the bar
- Try: only recurse if fewer than 2 sources were found on the first search
- Try: remove recursion entirely for max_depth=1 evals and see if it helps

### Secondary: Synthesizer Prompt Tuning

- Try a shorter, more direct output style focused on factual density
- Try instructing the synthesizer to always state confidence level on key claims
- Try requiring citations on every sentence that states a fact

## Workflow

For each experiment:
1. Make ONE focused change to `experiment.py`
2. Run: `uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json`
3. Read the composite score from the output
4. If composite > baseline:
   - `git add experiment.py && git commit -m "experiment: <description> (composite: X.XXX)"`
   - Update baseline to new score
5. If composite <= baseline:
   - `git checkout experiment.py`
   - Try the next direction

## Rules

- **Only edit `experiment.py`** — do not touch eval.py, backend/, scripts/, or any other file
- **One change at a time** — don't compound multiple changes before testing
- **Commit improvements** — git history is your experiment log
- **Revert failures** — use `git checkout experiment.py` to restore the last working version
```

- [ ] **Step 2: Commit**

```bash
git add program.md
git commit -m "docs: add autoresearch program.md with research directions"
```

---

### Task 4: Verify end-to-end wiring

**Files:** none (verification only)

- [ ] **Step 1: Confirm `--experiment` flag imports from `experiment.py`**

```bash
cd /home/anselmlong/Projects/bonsai && python -c "
import sys
sys.argv = ['eval.py', '--experiment', '--n', '1']
# Verify the import path resolves correctly without running the eval
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location('experiment', pathlib.Path('experiment.py'))
assert spec is not None, 'experiment.py not found'
print('experiment.py found and importable')
from experiment import run_research
print(f'run_research: {run_research}')
"
```

Expected output:
```
experiment.py found and importable
run_research: <function run_research at 0x...>
```

- [ ] **Step 2: Run full test suite one final time**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/ -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit if any fixups needed, otherwise done**

```bash
git log --oneline -5
```

Expected: see commits for experiment.py, eval.py changes, and program.md.
