#!/usr/bin/env python3
"""SimpleQA evaluation harness for Bonsai.

Usage:
    python scripts/eval.py --n 50 --output results/eval.json

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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset
from openai import OpenAI

from backend.agents.research_graph import run_research
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


class EvalResult(TypedDict):
    question: str
    gold_answer: str
    agent_answer: str
    latency_s: float
    branch_count: int
    source_count: int
    scores: dict[str, float]
    error: str | None


def grade_answer(client: OpenAI, question: str, gold: str, answer: str) -> dict[str, float]:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question, gold=gold, answer=answer
        )}],
        response_format={"type": "json_object"},
    )
    scores = json.loads(response.choices[0].message.content)
    return {dim: float(scores.get(dim, 0.0)) for dim in DIMENSIONS}


async def evaluate_question(
    question: str,
    gold_answer: str,
    config: dict,
    oai_client: OpenAI,
) -> EvalResult:
    queue: asyncio.Queue = asyncio.Queue()
    start = time.time()
    try:
        result = await run_research(
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


async def main(n: int, output_path: str, concurrency: int = 3) -> None:
    print(f"Loading SimpleQA dataset (first {n} questions)…")
    ds = load_dataset("openai/simple-evals", "simpleqa", split="test")
    samples = list(ds.select(range(n)))

    config = settings.research_config()
    config["max_branches"] = 3
    config["max_depth"] = 1   # keep eval fast

    oai_client = OpenAI(api_key=settings.openai_api_key)
    results: list[EvalResult] = []
    sem = asyncio.Semaphore(concurrency)

    async def run_with_sem(s):
        async with sem:
            r = await evaluate_question(s["problem"], s["answer"], config, oai_client)
            print(f"  {'✓' if r['scores']['factual_accuracy'] >= 0.7 else '✗'} {s['problem'][:60]}")
            return r

    print(f"Running {n} questions (concurrency={concurrency})…")
    results = await asyncio.gather(*[run_with_sem(s) for s in samples])

    # Write JSONL
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Summary
    valid = [r for r in results if not r["error"]]
    correct = [r for r in valid if r["scores"]["factual_accuracy"] >= 0.7]
    avg_scores = {
        dim: sum(r["scores"][dim] for r in valid) / len(valid)
        for dim in DIMENSIONS
    } if valid else {}
    avg_latency = sum(r["latency_s"] for r in valid) / len(valid) if valid else 0
    avg_sources = sum(r["source_count"] for r in valid) / len(valid) if valid else 0

    print(f"""
─────────────────────────────────────
SimpleQA Eval — bonsai
Questions:        {n}
Errors:           {len(results) - len(valid)}
Correct (≥0.7):   {len(correct)}  ({100*len(correct)/n:.1f}%)
Avg latency:      {avg_latency:.1f}s
Avg sources:      {avg_sources:.1f}
─────────────────────────────────────
Dimension scores:""")
    for dim, score in avg_scores.items():
        print(f"  {dim:<22} {score:.2f}")
    print(f"─────────────────────────────────────")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Number of questions to evaluate")
    parser.add_argument("--output", type=str, default="results/eval.json", help="Output JSONL path")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel requests")
    args = parser.parse_args()
    asyncio.run(main(args.n, args.output, args.concurrency))
