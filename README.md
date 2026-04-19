# Bonsai


https://github.com/user-attachments/assets/52b7f8c2-be23-4f93-ae03-57174c5b9c7c


Bonsai is a multi-agent deep research system, with an emphasis on traceability. Given a query, Bonsai decomposes it into a tree of sub-questions, researches each branch in parallel, and synthesises a final answer — with every intermediate step visible in real time. 

Bonsai achieves 65% correctness on the SimpleQA evaluation dataset (n = 20) at a threshold of 0.7 using LLM-as-judge. For comparison, GPT o3 currently sits at 50.5%. 

Try out Bonsai live at [bonsai.anselmlong.com](bonsai.anselmlong.com).

## Repository Layout

```
bonsai/
├── backend/               # FastAPI backend
│   ├── agents/           # Research agents (BranchProcessor, etc.)
│   │   ├── branch_processor.py
│   │   ├── research_graph.py
│   │   └── searcher.py
│   │   └── prompts/      # LangChain prompts
│   │       ├── planner.md
│   │       ├── reflect.md
│   │       └── synthesizer.md
│   ├── models/           # Data models and types
│   │   ├── __init__.py
│   │   └── types.py
│   ├── config.py         # Configuration/settings
│   ├── main.py           # API entry point (FastAPI)
│   ├── Dockerfile
│   └── tests/            # Unit & integration tests
├── frontend/             # Next.js frontend
│   ├── app/              # Next.js app router pages
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── research/
│   ├── components/       # React components
│   │   ├── AnswerRenderer.tsx
│   │   ├── GraphView.tsx
│   │   ├── NodeDetail.tsx
│   │   ├── QueryInput.tsx
│   │   ├── ResearchTree.tsx
│   │   ├── SourceCard.tsx
│   │   ├── StatusBar.tsx
│   │   └── TreePanel.tsx
│   ├── hooks/            # React hooks
│   │   ├── useResearchStream.ts
│   │   └── useResearchTree.ts
│   ├── lib/              # Shared utilities/types
│   │   └── types.ts
│   ├── public/           # Static assets
│   └── tsconfig.json
├── scripts/              # Utility scripts
│   └── eval.py           # Evaluation script (SimpleQA benchmark)
├── docs/                 # Documentation/iterations
│   ├── ITERATION_1.md
│   └── ITERATION_2.md
├── .env.example          # Environment template
├── .env                  # Environment variables (local)
├── docker-compose.yml    # Docker compose setup
├── pyproject.toml        # Python project config
└── uv.lock               # Python lockfile
```

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

Dev Script: 
```
./dev.sh
```
This development script runs both the backend and frontend simultaneously. If you wish to run them separately, refer to the next 2 commands.

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

### Results (SimpleQA, n=20)

| Metric | Score |
|--------|-------|
| **Correct (≥0.7)** | 13/20 (65%) |
| Avg latency | 30.1s |
| Avg sources | 4.4 |

| Dimension | Score |
|-----------|-------|
| factual_accuracy | 0.70 |
| citation_accuracy | 0.88 |
| completeness | 0.76 |
| source_quality | 0.82 |
| conciseness | 0.72 |

## Potential Improvements

This was done as a take home assignment as part of an interview. Given more time (and money), I plan to:
- Use stronger search APIs like Exa 
- Could consider searching first, then branching out subqueries from there 
- Iterating on the system prompts to get better outputs 
- The current graph view is not very smooth, some frontend iterations could fix that too.
