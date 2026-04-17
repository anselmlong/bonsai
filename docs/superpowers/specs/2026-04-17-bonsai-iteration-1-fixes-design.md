# Bonsai Iteration 1 — Bug Fixes & Features
**Design Spec · 2026-04-17**

## Overview

Five targeted fixes addressing usability and correctness issues discovered after the initial implementation. No visual redesign (deferred to Iteration 2). All changes are scoped to existing files — no new routes, no new backend endpoints beyond what already exists.

---

## Fix 1: Richer Synthesizer Output

### Problem
`synthesize_answer` passes only top-level branch summaries to the LLM. Sub-branch summaries (on `BranchResult.sub_branches`) are ignored. The synthesizer prompt targets 3–6 paragraphs, producing thin output.

### Solution

**`backend/agents/nodes/synthesizer.py`**

Add a recursive helper `flatten_branch_text(branch, depth) -> str` that walks the full branch tree and builds a structured text block:

```
Branch: <question>
Summary: <summary>
Sources: <url1>, <url2>
  Sub-branch: <child question>
  Summary: <child summary>
  Sources: <child urls>
    Sub-branch: <grandchild question>
    ...
```

Pass this full tree text to the synthesizer instead of the current flat summary list.

**`backend/agents/prompts/synthesizer.md`**

Update to request a research article:
- Opening paragraph establishing the main finding
- One section per major research branch (with sub-findings woven in)
- Inline citations: `[Source Title](url)` format
- Closing paragraph with synthesis and caveats
- Target length: 600–1200 words depending on complexity
- Do not use headers or bullet points — flowing prose only

### Files changed
- `backend/agents/nodes/synthesizer.py`
- `backend/agents/prompts/synthesizer.md`

---

## Fix 2: SSE Stream Stays Alive for Dive Deeper

### Problem
After initial research completes:
1. `run_research` puts `None` sentinel on the queue → SSE generator closes server-side
2. `useResearchStream` calls `es.close()` on `research_complete` → EventSource closes client-side

Subsequent dive-deeper events never reach the frontend.

### Solution

**`backend/agents/research_graph.py`**

Remove `await event_queue.put(None)`. The SSE generator now waits on the queue indefinitely. FastAPI's async generator handles client disconnect cleanup automatically.

**`backend/main.py`**

No change to the SSE generator needed — it already loops on `queue.get()` and breaks on `None`. With `None` removed from `run_research`, the generator stays alive for the session.

**`frontend/hooks/useResearchStream.ts`**

Remove `es.close()` on `research_complete`. Keep `setDone(true)` so the UI reflects completion, but leave the EventSource open. New branch events from dive-deeper continue to arrive and flow through `useResearchTree` normally — the tree updates in place.

The EventSource is closed only via the cleanup function returned from `useEffect` (i.e. when the component unmounts).

### Files changed
- `backend/agents/research_graph.py`
- `frontend/hooks/useResearchStream.ts`

---

## Fix 3: Inline Search Bar That Moves to the Nav

### Problem
No way to start a new query from the results page.

### Solution

**New component: `frontend/components/QueryInput.tsx`**

Accepts `variant: "hero" | "nav"` prop:
- `hero`: full centered layout — large input, submit button, used on home page
- `nav`: compact inline form — fits in the nav bar, smaller font, no sub-heading

On submit (both variants): POST to `/research`, navigate to `/research/[jobId]`.

**`frontend/app/page.tsx`**

Replace the inline form with `<QueryInput variant="hero" />`.

**`frontend/components/ResearchTree.tsx`**

Replace the static `<span className={styles.navLabel}>deep research</span>` with `<QueryInput variant="nav" />`.

### Files changed
- `frontend/components/QueryInput.tsx` (new)
- `frontend/components/QueryInput.module.css` (new)
- `frontend/app/page.tsx`
- `frontend/components/ResearchTree.tsx`

---

## Fix 4: Graph View Shows NodeDetail Panel

### Problem
Clicking a node in graph view calls `onSelect` but no detail panel renders — graph view is full-width with no sibling panel. Nodes also truncate questions too aggressively.

### Solution

**`frontend/components/ResearchTree.tsx`**

In graph view mode, render a flex row with:
- `<GraphView>` at `flex: 1, minWidth: 0` (shrinks when detail is open)
- `<NodeDetail>` at `width: 420px, flexShrink: 0` — only rendered when `selected !== null`

When `selected === null`, graph fills full width. Behaviour is consistent with tree view.

**`frontend/components/GraphView.tsx`**

- Increase node `width` from `180` to `220`
- Raise question character slice from `50` to `70`

### Files changed
- `frontend/components/ResearchTree.tsx`
- `frontend/components/GraphView.tsx`

---

## Fix 5: TreePanel Scrollbar Theming

### Problem
The tree panel uses the browser default scrollbar, which clashes with the dark theme.

### Solution

Add `::-webkit-scrollbar` rules to `.panel` in `TreePanel.module.css`:
- Width: 6px
- Track: `var(--surface-2)`
- Thumb: `var(--border-2)`
- Thumb on hover: `var(--amber)`

### Files changed
- `frontend/components/TreePanel.module.css`

---

## Testing

| Fix | How to verify |
|---|---|
| Synthesizer | Run a multi-branch query; final answer should be 600–1200 words of flowing prose with citations and sub-branch findings |
| Dive deeper stream | Click Dive Deeper on a complete node; new branches should appear in the tree without a page reload |
| Inline search | From results page, type a new query in the nav bar and submit; navigates to new job |
| Graph + NodeDetail | Switch to graph view, click a node; detail panel opens to the right |
| Scrollbar | Scroll the tree panel; scrollbar matches the dark theme |

---

## Out of Scope

- Visual redesign (Iteration 2)
- Backend changes to dive-deeper endpoint
- Integration tests (existing unit tests sufficient for backend changes)
