# Bonsai — Multi-Agent Deep Research System
**Design Spec · 2026-04-17**

## Overview

Bonsai is a multi-agent deep research system that takes a user query, decomposes it into a tree of sub-questions, researches each branch in parallel, and synthesises a final answer. Research nodes are streamed to a frontend in real time so users can observe, inspect, and extend the research process.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, LangGraph |
| Agent search | Tavily API |
| LLM — planner / synthesizer | GPT-4o (configurable) |
| LLM — researcher nodes | GPT-4o-mini (configurable) |
| Frontend | Next.js (React) |
| Graph visualization | React Flow |
| Streaming | Server-Sent Events (SSE) |
| Eval | standalone `scripts/eval.py` against SimpleQA |
| Tracing (optional) | LangSmith |

---

## Agent Architecture

### Two graph types

**`ResearchGraph` (root)** — orchestrates the full research job:
1. `planner` — analyzes the query, emits N sub-questions. Scaling rules are embedded in the system prompt: 1 agent for simple fact-finding (3–10 tool calls), 2–4 subagents for comparisons, 5+ for complex research. The number of sub-questions the planner generates *is* the scaling decision; `max_branches` is a hard cap.
2. `fan_out` — uses LangGraph's `Send` API to dispatch parallel `BranchGraph` invocations, one per sub-question.
3. `reduce` — waits for all branches to complete, collects `BranchResult[]`.
4. `synthesizer` — generates the final answer from all branch results.

**`BranchGraph` (subgraph, reusable)** — handles one sub-question:
1. `searcher` — calls Tavily, returns `SearchResult[]`.
2. `reflect` — evaluates search quality; decides whether to recurse.
3. Conditional edge: if `depth < max_depth` and reflection says "go deeper", spawns child `BranchGraph`s via `Send`.

Each `BranchGraph` is independently testable. It receives only `{question, depth, parent_summary, config}` — not the full research tree — to keep token usage low. LangGraph `MemorySaver` checkpointing enables resume-on-failure.

### Prompts as files

All system prompts live in `backend/agents/prompts/*.md`:
- `planner.md` — includes Anthropic's scaling rules verbatim
- `reflect.md` — criteria for deciding to recurse
- `synthesizer.md` — final answer format instructions

---

## State Schema

```python
class ResearchConfig(TypedDict):
    max_branches: int           # hard cap per level (default 5)
    max_depth: int              # hard cap on recursion depth (default 2)
    planner_model: str
    researcher_model: str
    synthesizer_model: str
    tavily_max_results: int     # default 5

class ResearchState(TypedDict):
    job_id: str
    query: str
    config: ResearchConfig
    sub_questions: list[str]
    branches: list[BranchResult]
    final_answer: str
    events: Annotated[list[NodeEvent], operator.add]  # append-only

class BranchState(TypedDict):
    node_id: str
    parent_id: str | None
    question: str
    parent_summary: str | None  # context from parent, not full state
    depth: int
    config: ResearchConfig
    search_results: list[SearchResult]
    sub_branches: list[BranchResult]
    summary: str
    sources: list[Source]

class NodeEvent(TypedDict):
    type: Literal[
        "research_started", "plan_complete",
        "branch_started", "branch_searching", "branch_reflecting",
        "branch_spawning", "branch_complete",
        "synthesis_started", "research_complete", "error"
    ]
    node_id: str
    parent_id: str | None
    depth: int
    question: str | None
    sources: list[Source] | None    # present on branch_complete
    summary: str | None             # present on branch_complete
    answer: str | None              # present on research_complete
    timestamp: float

class Source(TypedDict):
    url: str
    title: str
    excerpt: str
    score: float  # Tavily relevance score

class BranchResult(TypedDict):
    node_id: str
    question: str
    summary: str
    sources: list[Source]
    depth: int
```

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/research` | Start a research job. Body: `{query, config?}`. Returns `{job_id}`. |
| `GET` | `/research/{job_id}/stream` | SSE stream of `NodeEvent` objects. |
| `GET` | `/research/{job_id}/result` | Final result once complete (polling fallback). |
| `POST` | `/research/{job_id}/dive-deeper` | Spawn a new `BranchGraph` from a specific node. Body: `{node_id}`. |

**SSE transport:** FastAPI runs each research job as a background `asyncio` task. Every `NodeEvent` emitted by the graph is pushed to a per-job `asyncio.Queue`. The `/stream` endpoint drains the queue and sends each event as an SSE message. The frontend builds the full research tree purely from `node_id` + `parent_id` on each event — no separate state sync needed.

---

## Frontend

**Framework:** Next.js with React Flow for graph view.

**Layout — Split Panel (primary):**
- Left: `TreePanel` — collapsible indented tree, color-coded by node status (amber pulse = active, green = complete, grey = queued). Clicking a node selects it.
- Right: `NodeDetail` — selected node's summary (Spectral serif), sub-questions generated, sources with Tavily scores, and a "Dive Deeper" button.
- Toggle in nav: `TreePanel` ↔ `GraphView` (React Flow, same data, live animated).

**Key hooks:**
- `useResearchStream` — owns the `EventSource` connection, emits raw `NodeEvent[]`.
- `useResearchTree` — converts flat `NodeEvent[]` into the tree structure the UI renders. Independently testable.

**Design system** (see `.impeccable.md` for full details):
- UI chrome: **Bricolage Grotesque** (variable)
- Body / summaries / excerpts: **Spectral** (serif, italic for excerpts)
- Metadata / labels / scores: **Azeret Mono**
- Theme: dark cool-slate (`oklch(14% 0.012 250)`) + amber accent (`oklch(72% 0.12 95)`)

---

## Eval — `scripts/eval.py`

Standalone script, no app dependencies. Run independently of the FastAPI server.

```
python scripts/eval.py --n 50 --output results/eval-2026-04-17.json
```

**Pipeline:**
1. Load N questions from the SimpleQA dataset (HuggingFace or local CSV).
2. Run each question through the research agent asynchronously (configurable concurrency).
3. Grade each answer with LLM-as-judge across 5 dimensions: `factual_accuracy`, `citation_accuracy`, `completeness`, `source_quality`, `conciseness`.
4. Write per-question JSONL + print summary report.

The summary report is suitable for inclusion in the README as a benchmark result.

---

## Project Structure

```
bonsai/
├── backend/
│   ├── main.py                     # FastAPI app, routes, SSE
│   ├── config.py                   # ResearchConfig, env vars (pydantic-settings)
│   ├── agents/
│   │   ├── research_graph.py       # ResearchGraph
│   │   ├── branch_graph.py         # BranchGraph subgraph
│   │   ├── nodes/
│   │   │   ├── planner.py
│   │   │   ├── searcher.py
│   │   │   ├── reflect.py
│   │   │   └── synthesizer.py
│   │   └── prompts/
│   │       ├── planner.md          # scaling rules embedded here
│   │       ├── reflect.md
│   │       └── synthesizer.md
│   ├── models/
│   │   └── types.py                # NodeEvent, BranchState, ResearchState, etc.
│   └── tests/
│       ├── test_nodes.py           # unit: individual node functions (mocked)
│       ├── test_branch_graph.py    # unit: BranchGraph in isolation (mocked)
│       └── test_research_graph.py  # integration: real Tavily + LLM (@pytest.mark.slow)
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── research/[jobId]/page.tsx
│   ├── components/
│   │   ├── ResearchTree.tsx
│   │   ├── TreePanel.tsx
│   │   ├── NodeDetail.tsx
│   │   ├── GraphView.tsx           # React Flow (lazy-loaded)
│   │   ├── SourceCard.tsx
│   │   └── StatusBar.tsx
│   ├── hooks/
│   │   ├── useResearchStream.ts
│   │   └── useResearchTree.ts
│   └── lib/
│       └── types.ts                # mirrors backend/models/types.py
├── scripts/
│   └── eval.py
├── .env.example                    # OPENAI_API_KEY, TAVILY_API_KEY, LANGSMITH_API_KEY
├── pyproject.toml
└── README.md
```

---

## Testing Strategy

| Tier | File | What it tests | Speed |
|---|---|---|---|
| Unit | `test_nodes.py` | Each node function: state in → state out. LLM + Tavily mocked. | Fast |
| Unit | `test_branch_graph.py` | BranchGraph: recursion logic, depth capping, event emission. Mocked. | Fast |
| Integration | `test_research_graph.py` | Full graph with real Tavily + LLM. Marked `@pytest.mark.slow`. | Slow |
| Eval | `scripts/eval.py` | SimpleQA accuracy + LLM-as-judge 5-dimension scoring. | Slow |

---

## Key Design Decisions & Rationale

- **Scaling rules in prompt, not a classifier node** — following Anthropic's production finding that embedded guidelines outperform separate routing steps. The planner's sub-question count is the scaling decision.
- **`BranchState` inputs are slim** — only `{question, depth, parent_summary, config}` passed to each branch. Token efficiency explains 80% of performance variance (Anthropic).
- **`asyncio.Queue` per job** — graph runs as a background task, events pushed to queue, SSE drains it. No database needed, no polling.
- **Frontend tree built from SSE events alone** — `node_id + parent_id` on each event is sufficient. No extra state sync endpoint.
- **LangGraph `MemorySaver`** — free checkpoint-based error recovery. Resume from last good node on failure.
- **Tavily as search tool** — native LangChain/LangGraph integration, agent-native result schema, 1k free credits/month covers development.
- **Optional LangSmith tracing** — enabled by setting `LANGSMITH_API_KEY`. Full run traces available; linked from the frontend status bar.
