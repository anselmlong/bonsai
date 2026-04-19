# Graph-First Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the graph the primary view during research, show a dismissible banner when synthesis completes, and reveal a tabbed Summary / Research Graph / Tree layout after the user dismisses.

**Architecture:** Replace the `view: "tree" | "graph"` toggle in ResearchTree with a `phase: "researching" | "banner" | "summary"` state machine. Graph fills the viewport during research. When `finalAnswer` arrives, phase advances to `"banner"`. Clicking the banner advances to `"summary"`, which renders a three-tab layout. Remove dive deeper entirely (frontend + backend).

**Tech Stack:** React 18, Next.js (App Router), CSS Modules, FastAPI

---

## File Map

| File | Change |
|------|--------|
| `backend/main.py` | Remove `DiveDeeperRequest` model and `POST /research/{job_id}/dive-deeper` endpoint |
| `frontend/components/NodeDetail.tsx` | Remove `jobId` + `allNodes` props, `handleDiveDeeper` fn, dive deeper button |
| `frontend/components/NodeDetail.module.css` | Remove `.diveBtn` style |
| `frontend/components/ResearchTree.tsx` | Replace `view` state with `phase` + `activeTab`; new render logic |
| `frontend/components/ResearchTree.module.css` | Add banner, tab bar, fade-in styles; remove toggle styles |

---

### Task 1: Remove dive deeper from backend

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Delete `DiveDeeperRequest` and the dive-deeper endpoint from `main.py`**

Replace lines 33-36 (the `DiveDeeperRequest` model) and lines 83-107 (the full `dive_deeper` endpoint) with nothing. The file after the edit should end at the `get_result` endpoint. Final `main.py`:

```python
import asyncio
import json
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.research_graph import run_research
from backend.config import settings
from backend.models.types import NodeEvent, ResearchConfig

app = FastAPI(title="Bonsai Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store: job_id → {queue, task, result}
_jobs: dict[str, dict] = {}


class ResearchRequest(BaseModel):
    query: str
    config: dict | None = None


@app.post("/research")
async def start_research(req: ResearchRequest):
    job_id = uuid.uuid4().hex
    config: ResearchConfig = settings.research_config()
    if req.config:
        config.update(req.config)

    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {"queue": queue, "result": None}

    async def _run():
        result = await run_research(job_id, req.query, config, queue)
        _jobs[job_id]["result"] = result

    asyncio.create_task(_run())
    return {"job_id": job_id}


@app.get("/research/{job_id}/stream")
async def stream_research(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    queue: asyncio.Queue = _jobs[job_id]["queue"]

    async def event_generator() -> AsyncIterator[str]:
        while True:
            event = await queue.get()
            if event is None:  # sentinel
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/research/{job_id}/result")
async def get_result(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    result = _jobs[job_id].get("result")
    if result is None:
        return {"status": "in_progress"}
    return {"status": "complete", **result}
```

- [ ] **Step 2: Verify the backend still starts**

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Expected: `Application startup complete.` with no errors. Ctrl-C to stop.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: remove dive deeper endpoint"
```

---

### Task 2: Remove dive deeper from NodeDetail

**Files:**
- Modify: `frontend/components/NodeDetail.tsx`
- Modify: `frontend/components/NodeDetail.module.css`

- [ ] **Step 1: Rewrite `NodeDetail.tsx`**

Remove `API_BASE`, `jobId`, `allNodes`, `handleDiveDeeper`, and the dive deeper button. New file:

```tsx
"use client";
import type { TreeNode } from "@/lib/types";
import { SourceCard } from "./SourceCard";
import styles from "./NodeDetail.module.css";

interface NodeDetailProps {
  node: TreeNode;
  onSelect: (node: TreeNode) => void;
}

export function NodeDetail({ node, onSelect }: NodeDetailProps) {
  const subNodes = node.children;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div>
          <div className={styles.badge}>
            Branch · Depth {node.depth} · {node.status}
          </div>
          <h2 className={styles.title}>{node.question}</h2>
        </div>
      </div>

      {node.summary && (
        <section className={styles.section}>
          <div className={styles.label}>Summary</div>
          <p className={styles.summary}>{node.summary}</p>
        </section>
      )}

      {subNodes.length > 0 && (
        <section className={styles.section}>
          <div className={styles.label}>Sub-questions explored</div>
          <div className={styles.subqList}>
            {subNodes.map((child) => (
              <button
                key={child.id}
                className={styles.subqItem}
                onClick={() => onSelect(child)}
              >
                ↳ {child.question}
              </button>
            ))}
          </div>
        </section>
      )}

      {node.sources.length > 0 && (
        <section className={styles.section}>
          <div className={styles.label}>Sources ({node.sources.length})</div>
          <div className={styles.sourceList}>
            {node.sources.map((s) => (
              <SourceCard key={s.url} source={s} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Remove `.diveBtn` from `NodeDetail.module.css`**

Search for `.diveBtn` in `frontend/components/NodeDetail.module.css` and delete that rule. Leave all other rules intact.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/NodeDetail.tsx frontend/components/NodeDetail.module.css
git commit -m "feat: remove dive deeper from NodeDetail"
```

---

### Task 3: Add phase state machine to ResearchTree

**Files:**
- Modify: `frontend/components/ResearchTree.tsx`

This task rewrites ResearchTree.tsx. Read the current file before editing.

- [ ] **Step 1: Replace the full content of `ResearchTree.tsx`**

```tsx
"use client";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { AnswerRenderer } from "./AnswerRenderer";
import { useResearchStream } from "@/hooks/useResearchStream";
import { useResearchTree } from "@/hooks/useResearchTree";
import { TreePanel } from "./TreePanel";
import { NodeDetail } from "./NodeDetail";
import { StatusBar } from "./StatusBar";
import { QueryInput } from "./QueryInput";
import type { TreeNode } from "@/lib/types";
import styles from "./ResearchTree.module.css";

const GraphView = dynamic(() => import("./GraphView").then((m) => m.GraphView), {
  ssr: false,
});

type Phase = "researching" | "banner" | "summary";
type ActiveTab = "summary" | "graph" | "tree";

interface ResearchTreeProps {
  jobId: string;
}

export function ResearchTree({ jobId }: ResearchTreeProps) {
  const { events, done } = useResearchStream(jobId);
  const { rootNodes, nodeMap, finalAnswer } = useResearchTree(events);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("researching");
  const [activeTab, setActiveTab] = useState<ActiveTab>("summary");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (finalAnswer && phase === "researching") {
      setPhase("banner");
    }
  }, [finalAnswer, phase]);

  const handleCopy = () => {
    if (!finalAnswer) return;
    const plain = finalAnswer
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "")
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
    navigator.clipboard.writeText(plain).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const selected = selectedId ? (nodeMap.get(selectedId) ?? null) : null;

  const allNodes = [...nodeMap.values()];
  const completeCount = allNodes.filter((n) => n.status === "complete").length;
  const sourceCount = allNodes.reduce((sum, n) => sum + n.sources.length, 0);
  const maxDepth = allNodes.reduce((max, n) => Math.max(max, n.depth), 0);

  const handleSelect = (node: TreeNode) =>
    setSelectedId((prev) => (prev === node.id ? null : node.id));

  const handleDismissBanner = () => {
    setPhase("summary");
    setActiveTab("summary");
  };

  return (
    <div className={styles.shell}>
      <nav className={styles.nav}>
        <a href="/" className={styles.logo}>b<span>o</span>nsai</a>
        <span className={styles.navSep} />
        <QueryInput variant="nav" />
        <div className={styles.navSpacer} />
      </nav>

      {phase === "summary" ? (
        <div className={styles.summaryLayout}>
          <div className={styles.tabBar}>
            <button
              className={`${styles.tabBtn} ${activeTab === "summary" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("summary")}
            >
              Summary
            </button>
            <button
              className={`${styles.tabBtn} ${activeTab === "graph" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("graph")}
            >
              Research Graph
            </button>
            <button
              className={`${styles.tabBtn} ${activeTab === "tree" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("tree")}
            >
              Tree
            </button>
          </div>

          <div className={styles.tabContent}>
            {/* Summary tab */}
            <div className={`${styles.tabPanel} ${activeTab === "summary" ? styles.tabPanelActive : ""}`}>
              <div className={styles.detail}>
                {selected ? (
                  <>
                    <div className={styles.backBar}>
                      <button className={styles.backBtn} onClick={() => setSelectedId(null)}>
                        ← Summary
                      </button>
                    </div>
                    <NodeDetail node={selected} onSelect={handleSelect} />
                  </>
                ) : finalAnswer ? (
                  <div className={styles.answer}>
                    <div className={styles.answerHeader}>
                      <div className={styles.answerLabel}>Final Answer</div>
                      <button
                        className={`${styles.copyBtn} ${copied ? styles.copied : ""}`}
                        onClick={handleCopy}
                      >
                        {copied ? "Copied" : "Copy"}
                      </button>
                    </div>
                    <div className={styles.answerText}>
                      <AnswerRenderer content={finalAnswer} />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            {/* Graph tab */}
            <div className={`${styles.tabPanel} ${activeTab === "graph" ? styles.tabPanelActive : ""}`}>
              <div className={styles.graphTabContainer}>
                <GraphView rootNodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
                {selected && (
                  <div className={styles.graphDetailPane}>
                    <NodeDetail node={selected} onSelect={handleSelect} />
                  </div>
                )}
              </div>
            </div>

            {/* Tree tab */}
            <div className={`${styles.tabPanel} ${activeTab === "tree" ? styles.tabPanelActive : ""}`}>
              <div className={styles.main}>
                <TreePanel nodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
                <div className={styles.detail}>
                  {selected ? (
                    <>
                      <div className={styles.backBar}>
                        <button className={styles.backBtn} onClick={() => setSelectedId(null)}>
                          ← Summary
                        </button>
                      </div>
                      <NodeDetail node={selected} onSelect={handleSelect} />
                    </>
                  ) : (
                    <div className={styles.placeholder}>
                      <span className={styles.placeholderArrow}>←</span>
                      Select a branch to inspect it
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className={styles.graphStage}>
          <GraphView rootNodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
          {selected && (
            <div className={styles.graphDetailPane}>
              <NodeDetail node={selected} onSelect={handleSelect} />
            </div>
          )}
          {phase === "banner" && (
            <div className={styles.banner}>
              <span className={styles.bannerText}>Summary ready</span>
              <button className={styles.bannerBtn} onClick={handleDismissBanner}>
                View results →
              </button>
            </div>
          )}
        </div>
      )}

      <StatusBar
        done={done}
        branchCount={allNodes.length}
        completeCount={completeCount}
        sourceCount={sourceCount}
        maxDepthReached={maxDepth}
      />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && bun run tsc --noEmit 2>&1
```

Expected: no errors. If `NodeDetail` prop errors appear, the `jobId`/`allNodes` props were not fully removed in Task 2 — re-check that task.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ResearchTree.tsx
git commit -m "feat: replace view toggle with phase state machine"
```

---

### Task 4: Update CSS for graph-first layout and tabs

**Files:**
- Modify: `frontend/components/ResearchTree.module.css`

- [ ] **Step 1: Replace the full content of `ResearchTree.module.css`**

```css
.shell { display: flex; flex-direction: column; height: 100vh; background: var(--bg); }

/* Nav */
.nav { display: flex; align-items: center; gap: 14px; padding: 0 16px; height: 44px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }
.logo { font-style: italic; font-weight: 400; font-size: 16px; letter-spacing: -.01em; text-decoration: none; color: inherit; }
.logo span { color: var(--amber); }
.navSep { width: 1px; height: 16px; background: var(--border); }
.navSpacer { flex: 1; }

/* Graph stage (researching + banner phases) */
.graphStage { position: relative; flex: 1; display: flex; overflow: hidden; }

/* Banner */
.banner {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 14px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px 18px;
  box-shadow: 0 4px 20px rgba(0,0,0,.12);
  animation: bannerIn 0.3s cubic-bezier(0,0,0.2,1) both;
  z-index: 10;
}
@keyframes bannerIn { from { opacity: 0; transform: translateX(-50%) translateY(8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
.bannerText { font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--text-2); }
.bannerBtn {
  font-family: var(--ff-ui); font-size: 9px; letter-spacing: .14em; text-transform: uppercase;
  padding: 5px 12px; border-radius: 3px; cursor: pointer;
  background: var(--text); color: var(--bg); border: none;
  transition: opacity 0.15s;
}
.bannerBtn:hover { opacity: 0.8; }

/* Summary phase layout */
.summaryLayout { display: flex; flex-direction: column; flex: 1; overflow: hidden; animation: fadeIn 0.4s ease both; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* Tab bar */
.tabBar { display: flex; gap: 0; border-bottom: 1px solid var(--border); background: var(--surface); flex-shrink: 0; padding: 0 16px; }
.tabBtn {
  padding: 10px 16px; font-family: var(--ff-ui); font-size: 9px; letter-spacing: .14em;
  text-transform: uppercase; background: transparent; border: none;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  color: var(--text-3); cursor: pointer; transition: color 0.15s, border-color 0.15s;
}
.tabBtn:hover { color: var(--text-2); }
.tabBtnActive { color: var(--text); border-bottom-color: var(--amber); }

/* Tab panels */
.tabContent { flex: 1; overflow: hidden; }
.tabPanel { display: none; height: 100%; }
.tabPanelActive { display: flex; }

/* Summary tab inner layout */
.detail { flex: 1; overflow-y: auto; }
.answer { padding: 24px; border-bottom: 1px solid var(--border); animation: answerReveal 0.35s cubic-bezier(0,0,0.2,1) both; }
@keyframes answerReveal { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.answerHeader { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.answerLabel { font-size: 8px; letter-spacing: .18em; text-transform: uppercase; color: var(--text-3); }
.copyBtn { font-family: var(--ff-ui); font-size: 8px; letter-spacing: .12em; text-transform: uppercase; color: var(--text-3); background: transparent; border: 1px solid var(--border); border-radius: 3px; padding: 3px 8px; cursor: pointer; transition: color 0.15s, border-color 0.15s, transform 0.1s; }
.copyBtn:hover { color: var(--amber); border-color: var(--amber); }
.copyBtn:active { transform: translateY(1px); }
.copyBtn.copied { color: var(--green); border-color: var(--green); }
.answerText { font-family: var(--ff-body); font-size: 14px; font-weight: 300; color: var(--text-2); line-height: 1.85; }
.answerText p { margin-bottom: 0.9em; }
.answerText p:last-child { margin-bottom: 0; }
.backBar { padding: 8px 24px; border-bottom: 1px solid var(--border); }
.backBtn { background: transparent; border: none; padding: 0; font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--text-3); cursor: pointer; transition: color 0.15s; }
.backBtn:hover { color: var(--amber); }
.placeholder { display: flex; align-items: center; justify-content: center; height: 100%; font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--text-3); gap: 8px; }
.placeholderArrow { opacity: .4; }
.generating { display: flex; align-items: center; justify-content: center; height: 100%; font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--text-3); gap: 10px; }
.generatingDot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); opacity: 0.7; animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 0.2; transform: scale(0.85); } 50% { opacity: 0.8; transform: scale(1.1); } }

/* Graph tab */
.graphTabContainer { display: flex; flex: 1; overflow: hidden; }

/* Tree tab */
.main { display: flex; flex: 1; overflow: hidden; }

/* Shared: graph detail pane */
.graphDetailPane { width: 420px; flex-shrink: 0; overflow: hidden; border-left: 1px solid var(--border); }
```

- [ ] **Step 2: Verify the dev server compiles without CSS errors**

```bash
cd frontend && bun run dev 2>&1 | head -20
```

Expected: `✓ Ready` with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ResearchTree.module.css
git commit -m "feat: graph-first CSS — banner, tabs, fade-in"
```

---

### Task 5: Manual smoke test

- [ ] **Step 1: Start frontend and backend**

Terminal 1:
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Terminal 2:
```bash
cd frontend && bun run dev
```

- [ ] **Step 2: Run a research query and verify the full flow**

1. Open `http://localhost:3000`
2. Submit a query (e.g. "What causes northern lights?")
3. Confirm: the graph view loads immediately as the primary view (no tree panel, no toggle buttons in nav)
4. Watch nodes appear in real time as research progresses
5. Click a node — confirm the right detail pane slides in with summary and sources (no Dive Deeper button)
6. Wait for synthesis to complete — confirm the banner appears at the bottom center: "Summary ready · View results →"
7. Click "View results →" — confirm the tabbed layout fades in with Summary as the active tab
8. Confirm the summary renders correctly with citations
9. Click "Research Graph" tab — confirm the graph is visible and interactive
10. Click "Tree" tab — confirm the tree panel renders with all branches

- [ ] **Step 3: Verify dive deeper is gone**

In browser DevTools Network tab, confirm no requests to `/research/{jobId}/dive-deeper` are made at any point.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: graph-first layout with summary transition"
```
