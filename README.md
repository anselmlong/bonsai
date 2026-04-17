# Bonsai

Multi-agent deep research system. Given a query, Bonsai decomposes it into a tree of sub-questions, researches each branch in parallel, and synthesises a final answer — with every intermediate step visible in real time.

## Architecture

- **LangGraph** orchestrates the top-level research pipeline (planner → parallel fan-out → synthesize)
- **BranchProcessor** handles recursive branch research (search → reflect → optional sub-branches)
- **FastAPI + SSE** streams `NodeEvent`s to the frontend as the research tree grows
- **Next.js** renders the live tree with a split-panel view and a React Flow graph toggle

## Setup

**Requirements:** Python 3.11+, Node 18+

```bash
# 1. Clone and install backend
pip install -e ".[dev]"

# 2. Set environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and TAVILY_API_KEY

# 3. Install frontend
cd frontend && npm install && cd ..
```

## Running

**Backend** (port 8000):
```bash
uvicorn backend.main:app --reload
```

**Frontend** (port 3000):
```bash
cd frontend && npm run dev
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
pytest backend/tests/ -v -m "not slow"

# Integration tests (requires API keys)
pytest backend/tests/ -v -m slow
```

## Eval

Run the SimpleQA benchmark against a subset of questions:

```bash
python scripts/eval.py --n 50 --output results/eval.json
```

Scores factual accuracy, citation accuracy, completeness, source quality, and conciseness using LLM-as-judge.
