# Bonsai Iteration 1 — Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five usability and correctness issues: richer synthesizer output, SSE stream kept alive for dive-deeper, inline search bar in the nav, NodeDetail panel in graph view, and themed scrollbar.

**Architecture:** All changes are isolated to existing files or small new components. Backend fixes are in the agent layer. Frontend fixes are all in `components/` and `hooks/` — no new routes or API endpoints.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, langchain-openai, Next.js 16, TypeScript, CSS Modules.

---

## File Map

```
backend/
  agents/
    nodes/
      synthesizer.py        ← add _flatten_branch helper, use recursive content
    prompts/
      synthesizer.md        ← rewrite for article format (600–1200 words)
    research_graph.py       ← remove None sentinel
  tests/
    test_synthesizer.py     ← add sub-branch content test, update _make_branch

frontend/
  components/
    QueryInput.tsx          ← new: hero + nav variants
    QueryInput.module.css   ← new
    ResearchTree.tsx        ← swap navLabel for QueryInput nav; add NodeDetail in graph mode
    ResearchTree.module.css ← add .graphDetailPane
    GraphView.tsx           ← wider nodes (220px), longer text slice (70 chars)
    GraphView.module.css    ← add min-width: 0 to .container
    TreePanel.module.css    ← add ::-webkit-scrollbar rules
  hooks/
    useResearchStream.ts    ← keep EventSource open on research_complete
  app/
    page.tsx                ← use <QueryInput variant="hero" />
    page.module.css         ← remove form/input/btn rules (moved to QueryInput)
```

---

## Task 1: Richer Synthesizer — Sub-branch Content + Article Prompt

**Files:**
- Modify: `backend/agents/nodes/synthesizer.py`
- Modify: `backend/agents/prompts/synthesizer.md`
- Modify: `backend/tests/test_synthesizer.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_synthesizer.py` (also update `_make_branch` to accept `sub_branches`):

```python
# Update _make_branch helper to support sub_branches
def _make_branch(question: str, summary: str, sub_branches=None) -> BranchResult:
    return BranchResult(
        node_id="abc123",
        question=question,
        summary=summary,
        sources=[Source(url="https://example.com", title="Ex", excerpt="Exc.", score=0.9)],
        depth=1,
        sub_branches=sub_branches or [],
    )


@patch("backend.agents.nodes.synthesizer.ChatOpenAI")
def test_synthesize_includes_sub_branch_summaries(mock_llm_class):
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    mock_llm.invoke.return_value.content = "Article."

    child = BranchResult(
        node_id="child1", question="Sub-question?", summary="Deep finding.",
        sources=[], depth=1, sub_branches=[],
    )
    branch = BranchResult(
        node_id="abc123", question="Main?", summary="Top summary.",
        sources=[Source(url="https://example.com", title="Ex", excerpt=".", score=0.9)],
        depth=0, sub_branches=[child],
    )

    synthesize_answer("Query", [branch], DEFAULT_CONFIG)

    human_msg = mock_llm.invoke.call_args[0][0][1].content
    assert "Deep finding." in human_msg
    assert "Sub-question?" in human_msg
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/anselmlong/Projects/bonsai
.venv/bin/pytest backend/tests/test_synthesizer.py::test_synthesize_includes_sub_branch_summaries -v
```
Expected: `AssertionError` — "Deep finding." not in human message.

- [ ] **Step 3: Update synthesizer.py with _flatten_branch helper**

Replace the entire content of `backend/agents/nodes/synthesizer.py`:

```python
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.models.types import BranchResult, ResearchConfig

PROMPT = (Path(__file__).parent.parent / "prompts" / "synthesizer.md").read_text()


def _flatten_branch(branch: BranchResult, depth: int = 0) -> str:
    indent = "  " * depth
    label = "Branch" if depth == 0 else "Sub-branch"
    lines = [
        f"{indent}{label}: {branch['question']}",
        f"{indent}Summary: {branch['summary']}",
    ]
    if branch["sources"]:
        lines.append(f"{indent}Sources: {', '.join(s['url'] for s in branch['sources'][:3])}")
    for child in branch.get("sub_branches", []):
        lines.append(_flatten_branch(child, depth + 1))
    return "\n".join(lines)


def synthesize_answer(
    query: str,
    branches: list[BranchResult],
    config: ResearchConfig,
) -> str:
    """Synthesize all branch and sub-branch results into a final research article."""
    llm = ChatOpenAI(model=config.get("synthesizer_model", "gpt-4o"))

    branches_text = "\n\n".join(_flatten_branch(b) for b in branches)

    response = llm.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"User query: {query}\n\nResearch findings:\n{branches_text}"),
    ])
    return response.content
```

- [ ] **Step 4: Update synthesizer.md**

Replace the entire content of `backend/agents/prompts/synthesizer.md`:

```markdown
You are a research synthesizer. Given a user query and a complete set of research findings — organized as branches and sub-branches — write a comprehensive research article.

## Format
- Write flowing prose. No bullet points. No headers.
- Begin with an opening paragraph that directly answers the query and states the most important finding.
- Develop the analysis over subsequent paragraphs, weaving in sub-branch findings where they deepen or qualify the main branches.
- Cite sources inline using [Source Title](url) format wherever a specific claim is supported.
- Close with a paragraph that synthesizes across branches, notes any tensions or contradictions, and states what remains uncertain.
- Target length: 600–1200 words depending on query complexity.

## Rules
- Integrate all branches and sub-branches coherently. Do not list them separately or reference the research structure.
- Do not use phrases like "According to our research" or "The branches show". Write as an author, not a reporter.
- If findings contradict each other, acknowledge it and explain the tension.
- Do not pad with meta-commentary about the research process.
```

- [ ] **Step 5: Run all synthesizer tests**

```bash
cd /home/anselmlong/Projects/bonsai
.venv/bin/pytest backend/tests/test_synthesizer.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Run full backend suite to verify no regressions**

```bash
.venv/bin/pytest backend/tests/ -v -m "not slow"
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/nodes/synthesizer.py backend/agents/prompts/synthesizer.md backend/tests/test_synthesizer.py
git commit -m "feat: synthesizer uses full branch tree and writes research article"
```

---

## Task 2: Remove SSE Sentinel — Keep Stream Alive for Dive Deeper

**Files:**
- Modify: `backend/agents/research_graph.py`

- [ ] **Step 1: Remove the None sentinel**

In `backend/agents/research_graph.py`, delete line 64:
```python
    await event_queue.put(None)  # sentinel — signals SSE stream to close
```

The file after the change ends with:
```python
    await event_queue.put(NodeEvent(
        type="research_complete", node_id="root", parent_id=None,
        depth=0, question=query, sources=None, summary=None,
        answer=final_answer, timestamp=time.time(),
    ))

    return {"branches": branches, "final_answer": final_answer}
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd /home/anselmlong/Projects/bonsai
.venv/bin/pytest backend/tests/test_research_graph.py backend/tests/test_main.py -v -m "not slow"
```
Expected: 4 passed. (The `test_stream_delivers_events` test uses its own `fake_run` that manually puts `None` — it is unaffected. The graph tests drain the queue with `while not queue.empty()` and filter `if e is not None` — also unaffected.)

- [ ] **Step 3: Commit**

```bash
git add backend/agents/research_graph.py
git commit -m "fix: remove SSE sentinel so stream stays alive for dive-deeper"
```

---

## Task 3: Fix useResearchStream — Keep EventSource Open

**Files:**
- Modify: `frontend/hooks/useResearchStream.ts`

- [ ] **Step 1: Update the onmessage handler**

Replace `frontend/hooks/useResearchStream.ts` with:

```typescript
"use client";
import { useEffect, useRef, useState } from "react";
import type { NodeEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useResearchStream(jobId: string | null) {
  const [events, setEvents] = useState<NodeEvent[]>([]);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setEvents([]);
    setDone(false);
    setError(null);

    const es = new EventSource(`${API_BASE}/research/${jobId}/stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: NodeEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);
        if (event.type === "research_complete") {
          setDone(true);
          // Keep EventSource open — dive-deeper events arrive on the same stream
        }
        if (event.type === "error") {
          setDone(true);
          es.close();
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      setError("Stream connection lost.");
      setDone(true);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  return { events, done, error };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/anselmlong/Projects/bonsai/frontend
npx tsc --noEmit 2>&1 | head -20
```
Expected: no output (zero errors).

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/hooks/useResearchStream.ts
git commit -m "fix: keep EventSource open after research_complete for dive-deeper"
```

---

## Task 4: QueryInput Component — Hero + Nav Variants

**Files:**
- Create: `frontend/components/QueryInput.tsx`
- Create: `frontend/components/QueryInput.module.css`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/page.module.css`
- Modify: `frontend/components/ResearchTree.tsx`
- Modify: `frontend/components/ResearchTree.module.css`

- [ ] **Step 1: Create frontend/components/QueryInput.tsx**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./QueryInput.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface QueryInputProps {
  variant: "hero" | "nav";
}

export function QueryInput({ variant }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    const res = await fetch(`${API_BASE}/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const { job_id } = await res.json();
    router.push(`/research/${job_id}`);
  };

  const isNav = variant === "nav";

  return (
    <form
      className={`${styles.form} ${isNav ? styles.formNav : styles.formHero}`}
      onSubmit={handleSubmit}
    >
      <input
        className={`${styles.input} ${isNav ? styles.inputNav : styles.inputHero}`}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={isNav ? "New research query…" : "What do you want to research?"}
        autoFocus={!isNav}
      />
      <button
        className={`${styles.btn} ${isNav ? styles.btnNav : styles.btnHero}`}
        type="submit"
        disabled={loading}
      >
        {loading ? "…" : "→"}
      </button>
    </form>
  );
}
```

- [ ] **Step 2: Create frontend/components/QueryInput.module.css**

```css
.form { display: flex; gap: 8px; }

/* Hero */
.formHero { width: 100%; max-width: 600px; }
.inputHero {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 10px 14px;
  font-family: var(--ff-ui);
  font-size: 14px;
  font-weight: 300;
  color: var(--text);
  outline: none;
}
.inputHero:focus { border-color: var(--amber); }
.btnHero {
  padding: 10px 18px;
  background: var(--amber-dim2);
  border: 1px solid var(--amber);
  border-radius: 5px;
  font-family: var(--ff-mono);
  font-size: 10px;
  color: var(--amber);
  letter-spacing: .06em;
  white-space: nowrap;
}

/* Nav */
.formNav { align-items: center; }
.inputNav {
  width: 220px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 10px;
  font-family: var(--ff-ui);
  font-size: 12px;
  font-weight: 300;
  color: var(--text);
  outline: none;
}
.inputNav:focus { border-color: var(--amber); }
.btnNav {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border-2);
  border-radius: 4px;
  font-family: var(--ff-mono);
  font-size: 10px;
  color: var(--text-2);
}
.btnNav:hover { border-color: var(--amber); color: var(--amber); }

.btn:disabled { opacity: .5; cursor: not-allowed; }
```

- [ ] **Step 3: Update frontend/app/page.tsx**

Replace with:

```tsx
import { QueryInput } from "@/components/QueryInput";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.main}>
      <h1 className={styles.logo}>b<span>o</span>nsai</h1>
      <p className={styles.sub}>deep research, every branch visible</p>
      <QueryInput variant="hero" />
    </main>
  );
}
```

Note: `page.tsx` no longer needs `"use client"` since `QueryInput` handles its own client state.

- [ ] **Step 4: Update frontend/app/page.module.css**

Remove the `.form`, `.input`, `.btn` rules (now in `QueryInput.module.css`). Replace with:

```css
.main { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: 16px; padding: 24px; }
.logo { font-size: 32px; font-weight: 600; letter-spacing: -.03em; }
.logo span { color: var(--amber); }
.sub { font-family: var(--ff-mono); font-size: 11px; color: var(--text-3); letter-spacing: .06em; margin-bottom: 16px; }
```

- [ ] **Step 5: Update frontend/components/ResearchTree.tsx**

Replace the `navLabel` span with `<QueryInput variant="nav" />`. Add `QueryInput` import at the top.

Change:
```tsx
import { StatusBar } from "./StatusBar";
```
to:
```tsx
import { StatusBar } from "./StatusBar";
import { QueryInput } from "./QueryInput";
```

Change:
```tsx
        <span className={styles.navSep} />
        <span className={styles.navLabel}>deep research</span>
```
to:
```tsx
        <span className={styles.navSep} />
        <QueryInput variant="nav" />
```

- [ ] **Step 6: Remove .navLabel from ResearchTree.module.css**

In `frontend/components/ResearchTree.module.css`, delete the line:
```css
.navLabel { font-family: var(--ff-mono); font-size: 10px; color: var(--text-3); letter-spacing: .05em; }
```

- [ ] **Step 7: Verify TypeScript compiles**

```bash
cd /home/anselmlong/Projects/bonsai/frontend
npx tsc --noEmit 2>&1 | head -20
```
Expected: no output.

- [ ] **Step 8: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/QueryInput.tsx frontend/components/QueryInput.module.css \
        frontend/app/page.tsx frontend/app/page.module.css \
        frontend/components/ResearchTree.tsx frontend/components/ResearchTree.module.css
git commit -m "feat: extract QueryInput component, add nav search bar"
```

---

## Task 5: Graph View + NodeDetail Split Panel

**Files:**
- Modify: `frontend/components/ResearchTree.tsx`
- Modify: `frontend/components/ResearchTree.module.css`
- Modify: `frontend/components/GraphView.tsx`
- Modify: `frontend/components/GraphView.module.css`

- [ ] **Step 1: Fix node width and text length in GraphView.tsx**

In `frontend/components/GraphView.tsx`, make two changes:

Change node `width` from `180` to `220`:
```tsx
      style: {
        background: "oklch(18% 0.010 250)",
        border: `1px solid ${selectedId === n.id ? "oklch(72% 0.12 95)" : "oklch(28% 0.010 250)"}`,
        borderRadius: "6px",
        color: "oklch(92% 0.008 250)",
        fontSize: "11px",
        width: 220,
      },
```

Change question slice from `50` to `70`:
```tsx
            <span className={styles.nodeQuestion}>{n.question.slice(0, 70)}{n.question.length > 70 ? "…" : ""}</span>
```

- [ ] **Step 2: Add min-width: 0 to GraphView.module.css**

In `frontend/components/GraphView.module.css`, update `.container`:
```css
.container { flex: 1; min-width: 0; height: 100%; }
```

- [ ] **Step 3: Add .graphDetailPane to ResearchTree.module.css**

Add to `frontend/components/ResearchTree.module.css`:
```css
.graphDetailPane { width: 420px; flex-shrink: 0; overflow: hidden; border-left: 1px solid var(--border); }
```

- [ ] **Step 4: Add NodeDetail panel in graph view mode in ResearchTree.tsx**

In `frontend/components/ResearchTree.tsx`, find the graph view section:
```tsx
        ) : (
          <GraphView rootNodes={rootNodes} selectedId={selected?.id ?? null} onSelect={setSelected} />
        )}
```

Replace with:
```tsx
        ) : (
          <>
            <GraphView rootNodes={rootNodes} selectedId={selected?.id ?? null} onSelect={setSelected} />
            {selected && (
              <div className={styles.graphDetailPane}>
                <NodeDetail node={selected} jobId={jobId} onSelect={setSelected} />
              </div>
            )}
          </>
        )}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd /home/anselmlong/Projects/bonsai/frontend
npx tsc --noEmit 2>&1 | head -20
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/ResearchTree.tsx frontend/components/ResearchTree.module.css \
        frontend/components/GraphView.tsx frontend/components/GraphView.module.css
git commit -m "feat: graph view shows NodeDetail panel on node click, wider nodes"
```

---

## Task 6: TreePanel Scrollbar Theming

**Files:**
- Modify: `frontend/components/TreePanel.module.css`

- [ ] **Step 1: Add scrollbar rules to TreePanel.module.css**

Append to `frontend/components/TreePanel.module.css`:

```css
.panel::-webkit-scrollbar { width: 6px; }
.panel::-webkit-scrollbar-track { background: var(--surface-2); }
.panel::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
.panel::-webkit-scrollbar-thumb:hover { background: var(--amber); }
```

- [ ] **Step 2: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/TreePanel.module.css
git commit -m "fix: theme TreePanel scrollbar with design tokens"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Richer synthesizer — recursive sub-branch content | Task 1 (`_flatten_branch`) |
| Richer synthesizer — article format prompt | Task 1 (synthesizer.md) |
| SSE stream stays alive for dive-deeper (backend) | Task 2 (remove sentinel) |
| SSE stream stays alive for dive-deeper (frontend) | Task 3 (keep EventSource open) |
| Inline search bar with hero + nav variants | Task 4 (QueryInput component) |
| Graph view shows NodeDetail on node click | Task 5 (split panel) |
| Graph node truncation fix | Task 5 (width 220, slice 70) |
| TreePanel scrollbar theming | Task 6 |

All spec requirements covered.

**Placeholder scan:** None found. All steps contain complete code.

**Type consistency:**
- `BranchResult` has `sub_branches: list` (added in original iteration). `_flatten_branch` calls `branch.get("sub_branches", [])` — safe.
- `QueryInput` props: `variant: "hero" | "nav"` — used consistently in page.tsx and ResearchTree.tsx.
- `NodeDetail` props: `node`, `jobId`, `onSelect` — matches the current component signature (Task 5 correctly omits the unused `allNodes`).
