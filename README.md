# Bonsai

Multi-agent deep research system. Given a query, Bonsai decomposes it into a tree of sub-questions, researches each branch in parallel, and synthesises a final answer — with every intermediate step visible in real time.

## Architecture

- **LangGraph** orchestrates the top-level research pipeline (planner → parallel fan-out → synthesize)
- **BranchProcessor** handles recursive branch research (search → reflect → optional sub-branches)
- **FastAPI + SSE** streams `NodeEvent`s to the frontend as the research tree grows
- **Next.js** renders the live research graph as branches expand in real time, then transitions to a tabbed summary view (Answer | Graph | Tree) when synthesis completes

## Setup

**Requirements:** Python 3.11+, Node 18+, [uv](https://github.com/astral-sh/uv), [bun](https://bun.sh)

```bash
# 1. Clone and install backend
uv sync

# 2. Set environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and TAVILY_API_KEY

# 3. Install frontend
cd frontend && bun install && cd ..
```

## Running

**Backend** (port 8000):
```bash
uv run uvicorn backend.main:app --reload
```

**Frontend** (port 3000):
```bash
cd frontend && bun dev
```

Open `http://localhost:3000` and enter a research query.

## CLI / curl

```bash
# Start a research job
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the long-term economic effects of remote work?"}' | jq .

# Stream events
curl -N http://localhost:8000/research/{job_id}/stream
```

## Tests

```bash
# Unit tests (fast, no API keys needed)
uv run pytest backend/tests/ -v -m "not slow"

# Integration tests (requires API keys)
uv run pytest backend/tests/ -v -m slow
```

## Eval

Run the SimpleQA benchmark against a subset of questions:

```bash
uv run python scripts/eval.py --n 50 --output results/eval.json
```

Scores factual accuracy, citation accuracy, completeness, source quality, and conciseness using LLM-as-judge.
