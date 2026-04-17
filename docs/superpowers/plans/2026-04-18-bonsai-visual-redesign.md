# Bonsai Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dark developer-tool aesthetic with a light parchment/editorial theme — forest green accent, Spectral serif throughout, no monospace font.

**Architecture:** CSS-only changes across 8 CSS Module files plus one TSX file (GraphView.tsx has hardcoded color strings that cannot be driven by CSS variables). All design tokens live in `globals.css` — updating them cascades to every component automatically. The TSX change is isolated to color constants and a `colorMode` prop.

**Tech Stack:** Next.js 16, CSS Modules, React Flow (`@xyflow/react`), Spectral (Google Fonts).

---

## File Map

```
frontend/
  app/
    globals.css              ← Task 1: rewrite tokens + swap font import
    page.module.css          ← Task 2: parchment home page
  components/
    QueryInput.module.css    ← Task 3: light input variants
    ResearchTree.module.css  ← Task 4: parchment shell + nav
    TreePanel.module.css     ← Task 5: parchment tree panel + serif labels
    NodeDetail.module.css    ← Task 6: editorial detail panel
    SourceCard.module.css    ← Task 7: parchment source cards
    StatusBar.module.css     ← Task 8: parchment status bar
    GraphView.tsx            ← Task 9: update hardcoded node/edge colors + colorMode
    GraphView.module.css     ← Task 9: add italic to nodeQuestion
```

---

## Task 1: Design Tokens — globals.css

**Files:**
- Modify: `frontend/app/globals.css`

This is the foundation. Every subsequent task inherits from these tokens. Do this first.

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/app/globals.css
```

- [ ] **Step 2: Replace entire file**

Write this as the complete content of `frontend/app/globals.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,400;0,500;1,300;1,400;1,500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:         #f5f0e8;
  --surface:    #ece6d8;
  --surface-2:  #e0d8c8;
  --border:     #d4c8b4;
  --border-2:   #c0b8a8;
  --text:       #2a2418;
  --text-2:     #5a5040;
  --text-3:     #a89e88;
  --amber:      #3d6b4a;
  --amber-dim:  rgba(61, 107, 74, 0.12);
  --amber-dim2: rgba(61, 107, 74, 0.06);
  --green:      #3d6b4a;
  --red:        #8b3a2a;
  --ff-ui:   'Spectral', Georgia, serif;
  --ff-body: 'Spectral', Georgia, serif;
  --ff-mono: 'Spectral', Georgia, serif;
}

html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--ff-ui); }
button { font-family: var(--ff-ui); cursor: pointer; }
```

Key changes from current:
- Font import: removed Bricolage Grotesque and Azeret Mono, added Spectral weights 300/400/500 in both normal and italic
- All `--bg`/`--surface`/`--border`/`--text` values → warm parchment palette
- `--amber` → forest green `#3d6b4a` (used everywhere the old amber was)
- `--amber-dim` / `--amber-dim2` → green-tinted alpha variants
- `--green` → same as `--amber` (unified accent)
- `--red` → muted terracotta `#8b3a2a`
- All three `--ff-*` vars → Spectral (so existing code using `var(--ff-mono)` automatically gets Spectral)

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/anselmlong/Projects/bonsai/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no output (CSS changes don't affect TS).

- [ ] **Step 4: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/app/globals.css
git commit -m "feat: redesign — parchment tokens, forest green accent, Spectral serif"
```

---

## Task 2: Home Page — page.module.css

**Files:**
- Modify: `frontend/app/page.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/app/page.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.main { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: 12px; padding: 24px; }
.logo { font-style: italic; font-size: 48px; font-weight: 400; letter-spacing: -.02em; color: var(--text); }
.logo span { color: var(--amber); }
.sub { font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); margin-bottom: 8px; }
```

Changes: logo is now Spectral italic at 48px (was Bricolage Grotesque 32px bold); subheading uses Spectral spaced caps instead of Azeret Mono.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/app/page.module.css
git commit -m "feat: redesign — parchment home page, Spectral italic logo"
```

---

## Task 3: Query Input — QueryInput.module.css

**Files:**
- Modify: `frontend/components/QueryInput.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/QueryInput.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.form { display: flex; gap: 8px; }

/* Hero */
.formHero { width: 100%; max-width: 520px; }
.inputHero {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 11px 16px;
  font-family: var(--ff-ui);
  font-style: italic;
  font-size: 14px;
  color: var(--text);
  outline: none;
}
.inputHero:focus { border-color: var(--amber); }
.btnHero {
  padding: 11px 20px;
  background: var(--amber);
  border: none;
  border-radius: 4px;
  font-family: var(--ff-ui);
  font-size: 9px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--bg);
  white-space: nowrap;
}

/* Nav */
.formNav { align-items: center; }
.inputNav {
  width: 180px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 4px 10px;
  font-family: var(--ff-ui);
  font-style: italic;
  font-size: 12px;
  color: var(--text);
  outline: none;
}
.inputNav:focus { border-color: var(--amber); }
.btnNav {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border-2);
  border-radius: 3px;
  font-family: var(--ff-ui);
  font-size: 9px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--text-3);
}
.btnNav:hover { border-color: var(--amber); color: var(--amber); }

.btnHero:disabled, .btnNav:disabled { opacity: .5; cursor: not-allowed; }
```

Key changes: inputs now use `font-style: italic`; hero button is solid green fill with parchment text (`var(--bg)`); nav button uses Spectral spaced caps instead of Azeret Mono.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/QueryInput.module.css
git commit -m "feat: redesign — parchment query input, italic placeholder, green submit"
```

---

## Task 4: Shell + Nav — ResearchTree.module.css

**Files:**
- Modify: `frontend/components/ResearchTree.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/ResearchTree.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.shell { display: flex; flex-direction: column; height: 100vh; background: var(--bg); }
.nav { display: flex; align-items: center; gap: 14px; padding: 0 16px; height: 44px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }
.logo { font-style: italic; font-weight: 400; font-size: 16px; letter-spacing: -.01em; }
.logo span { color: var(--amber); }
.navSep { width: 1px; height: 16px; background: var(--border); }.navSpacer { flex: 1; }
.toggle { display: flex; gap: 2px; }
.toggleBtn { padding: 4px 12px; border-radius: 3px; font-family: var(--ff-ui); font-size: 9px; letter-spacing: .16em; text-transform: uppercase; border: 1px solid transparent; color: var(--text-3); background: transparent; }
.toggleBtn.active { color: var(--text); background: var(--bg); border-color: var(--border); }
.main { display: flex; flex: 1; overflow: hidden; }
.detail { flex: 1; overflow: hidden; }
.answer { padding: 24px; }
.answerLabel { font-size: 8px; letter-spacing: .18em; text-transform: uppercase; color: var(--text-3); margin-bottom: 12px; }
.answerText { font-family: var(--ff-body); font-size: 14px; font-weight: 300; color: var(--text-2); line-height: 1.85; max-width: 65ch; }
.placeholder { display: flex; align-items: center; justify-content: center; height: 100%; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--text-3); }
.graphDetailPane { width: 420px; flex-shrink: 0; overflow: hidden; border-left: 1px solid var(--border); }
```

Key changes: nav is parchment surface; logo is Spectral italic; toggleBtn uses Spectral spaced caps; `.active` toggle shows parchment bg with border (inverts from dark theme); `answerLabel` and `placeholder` use Spectral spaced caps (no mono).

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/ResearchTree.module.css
git commit -m "feat: redesign — parchment nav shell, Spectral spaced caps toggles"
```

---

## Task 5: Tree Panel — TreePanel.module.css

**Files:**
- Modify: `frontend/components/TreePanel.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/TreePanel.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.panel { width: 220px; border-right: 1px solid var(--border); overflow-y: auto; padding: 10px 0; flex-shrink: 0; background: var(--surface); }
.header { padding: 0 14px 10px; font-size: 8px; letter-spacing: .18em; color: var(--text-3); text-transform: uppercase; }
.nodeWrap { display: flex; flex-direction: column; }
.row { display: flex; align-items: center; gap: 8px; padding: 6px 14px; cursor: pointer; user-select: none; }
.row:hover { background: var(--surface-2); }
.selected { background: var(--amber-dim2) !important; }
.selected .label { color: var(--amber); }
.indicator { font-size: 10px; width: 12px; text-align: center; flex-shrink: 0; }
.complete { color: var(--green); }
.searching, .reflecting, .spawning { color: var(--amber); opacity: .65; }
.pending { color: var(--text-3); }
.error { color: var(--red); }
.pulse { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.label { font-style: italic; font-size: 12px; color: var(--text-2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta { font-size: 9px; letter-spacing: .06em; color: var(--text-3); flex-shrink: 0; }
.children { padding-left: 14px; border-left: 1px solid var(--border); margin-left: 17px; }
.panel::-webkit-scrollbar { width: 6px; }
.panel::-webkit-scrollbar-track { background: var(--surface-2); }
.panel::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
.panel::-webkit-scrollbar-thumb:hover { background: var(--amber); }
```

Key changes: panel background is `var(--surface)` (slightly darker parchment); `.header` uses Spectral spaced caps; `.label` is now `font-style: italic`; panel width increased to 220px to match mockup; `.meta` uses Spectral spaced caps.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/TreePanel.module.css
git commit -m "feat: redesign — parchment tree panel, italic serif labels"
```

---

## Task 6: Node Detail — NodeDetail.module.css

**Files:**
- Modify: `frontend/components/NodeDetail.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/NodeDetail.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.panel { flex: 1; overflow-y: auto; padding: 20px 24px; }
.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; gap: 12px; }
.badge { font-size: 8px; letter-spacing: .18em; color: var(--green); text-transform: uppercase; margin-bottom: 5px; }
.title { font-style: italic; font-size: 18px; font-weight: 400; color: var(--text); letter-spacing: -.01em; line-height: 1.3; }
.diveBtn { padding: 6px 14px; background: transparent; border: 1px solid var(--amber); border-radius: 3px; font-family: var(--ff-ui); font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--amber); cursor: pointer; white-space: nowrap; flex-shrink: 0; transition: background .15s; }
.diveBtn:hover { background: var(--amber-dim2); }
.section { margin-bottom: 20px; }
.label { font-size: 8px; letter-spacing: .18em; text-transform: uppercase; color: var(--text-3); margin-bottom: 8px; }
.summary { font-family: var(--ff-body); font-size: 13px; font-weight: 300; color: var(--text-2); line-height: 1.85; border-left: 2px solid var(--amber-dim); padding-left: 14px; }
.subqList { display: flex; flex-direction: column; gap: 4px; }
.subqItem { padding: 6px 10px; background: var(--surface); border: 1px solid var(--border); border-radius: 3px; font-style: italic; font-size: 12px; font-weight: 300; color: var(--text-2); cursor: pointer; text-align: left; transition: border-color .15s; }
.subqItem:hover { border-color: var(--border-2); color: var(--text); }
.sourceList { display: flex; flex-direction: column; gap: 6px; }
```

Key changes: `.title` is Spectral italic 18px (was 16px sans-serif); `.summary` now has a green left-border accent instead of the surface-background box; `.diveBtn` is Spectral spaced caps with green border; `.badge` and `.label` use Spectral spaced caps; `.subqItem` is Spectral italic.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/NodeDetail.module.css
git commit -m "feat: redesign — editorial node detail, italic title, green summary border"
```

---

## Task 7: Source Cards — SourceCard.module.css

**Files:**
- Modify: `frontend/components/SourceCard.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/SourceCard.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.card {
  display: block;
  text-decoration: none;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  transition: border-color 0.15s;
}
.card:hover { border-color: var(--border-2); }
.top { display: flex; justify-content: space-between; margin-bottom: 4px; }
.domain { font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--amber); }
.score { font-size: 9px; letter-spacing: .06em; color: var(--green); }
.title { font-size: 12px; font-weight: 400; color: var(--text-2); margin-bottom: 4px; }
.excerpt { font-style: italic; font-size: 11px; font-weight: 300; color: var(--text-3); line-height: 1.65; margin: 0; }
```

Key changes: background is `var(--surface)` not a darker tone; `.domain` is Spectral spaced caps (was Azeret Mono); `.score` is Spectral spaced caps; `.excerpt` gains `font-style: italic`.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/SourceCard.module.css
git commit -m "feat: redesign — parchment source cards, italic excerpt"
```

---

## Task 8: Status Bar — StatusBar.module.css

**Files:**
- Modify: `frontend/components/StatusBar.module.css`

- [ ] **Step 1: Read current file**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/StatusBar.module.css
```

- [ ] **Step 2: Replace entire file**

```css
.bar { display: flex; align-items: center; gap: 12px; padding: 0 16px; height: 30px; background: var(--surface); border-top: 1px solid var(--border); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); }
.dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--amber); animation: pulse 1.4s ease-in-out infinite; flex-shrink: 0; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.active { color: var(--text-2); }
.done { color: var(--green); }
.sep { color: var(--border-2); }
.trace { color: var(--amber); margin-left: auto; text-decoration: none; }
.trace:hover { text-decoration: underline; }
```

Key changes: bar uses parchment surface and border tokens; all text is Spectral spaced caps (was Azeret Mono); `.dot` is green; height reduced to 30px for tighter look.

- [ ] **Step 3: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/StatusBar.module.css
git commit -m "feat: redesign — parchment status bar, Spectral spaced caps"
```

---

## Task 9: Graph View — GraphView.tsx + GraphView.module.css

**Files:**
- Modify: `frontend/components/GraphView.tsx`
- Modify: `frontend/components/GraphView.module.css`

GraphView hardcodes color strings directly in JSX (they can't be driven by CSS variables at the React Flow level). All `oklch(...)` values must be replaced with parchment palette hex values.

- [ ] **Step 1: Read both files**

```bash
cat /home/anselmlong/Projects/bonsai/frontend/components/GraphView.tsx
cat /home/anselmlong/Projects/bonsai/frontend/components/GraphView.module.css
```

- [ ] **Step 2: Replace GraphView.tsx**

Replace the entire content of `frontend/components/GraphView.tsx`:

```tsx
"use client";
import { useMemo } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  type Node, type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { TreeNode } from "@/lib/types";
import styles from "./GraphView.module.css";

const STATUS_COLOR: Record<TreeNode["status"], string> = {
  pending: "#c0b8a8",
  searching: "#3d6b4a",
  reflecting: "#3d6b4a",
  spawning: "#3d6b4a",
  complete: "#3d6b4a",
  error: "#8b3a2a",
};

function flattenNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.flatMap((n) => [n, ...flattenNodes(n.children)]);
}

interface GraphViewProps {
  rootNodes: TreeNode[];
  selectedId: string | null;
  onSelect: (node: TreeNode) => void;
}

export function GraphView({ rootNodes, selectedId, onSelect }: GraphViewProps) {
  const { rfNodes, rfEdges } = useMemo(() => {
    const all = flattenNodes(rootNodes);
    const rfNodes: Node[] = all.map((n, i) => ({
      id: n.id,
      position: { x: (i % 4) * 220, y: n.depth * 140 },
      data: {
        label: (
          <div className={styles.nodeLabel}>
            <span className={styles.nodeStatus} style={{ color: STATUS_COLOR[n.status] }}>
              {n.status === "complete" ? "✓" : "⟳"}
            </span>
            <span className={styles.nodeQuestion}>{n.question.slice(0, 70)}{n.question.length > 70 ? "…" : ""}</span>
          </div>
        ),
        treeNode: n,
      },
      style: {
        background: "#ece6d8",
        border: `1px solid ${selectedId === n.id ? "#3d6b4a" : "#d4c8b4"}`,
        borderRadius: "6px",
        color: "#2a2418",
        fontSize: "11px",
        width: 220,
      },
    }));

    const rfEdges: Edge[] = all
      .filter((n) => n.parentId && n.parentId !== "root")
      .map((n) => ({
        id: `${n.parentId}-${n.id}`,
        source: n.parentId!,
        target: n.id,
        style: { stroke: "#d4c8b4" },
        animated: n.status !== "complete",
      }));

    return { rfNodes, rfEdges };
  }, [rootNodes, selectedId]);

  return (
    <div className={styles.container}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={(_, node) => onSelect((node.data as { treeNode: TreeNode }).treeNode)}
        fitView
        colorMode="light"
      >
        <Background color="#e0d8c8" gap={16} />
        <Controls />
        <MiniMap nodeColor={(n) => STATUS_COLOR[(n.data as { treeNode: TreeNode }).treeNode.status]} />
      </ReactFlow>
    </div>
  );
}
```

Changes from current:
- `STATUS_COLOR`: pending `#374151` → `#c0b8a8`; searching/reflecting/spawning `oklch(72% 0.12 95)` → `#3d6b4a`; complete `oklch(68% 0.14 155)` → `#3d6b4a`; error `oklch(62% 0.14 25)` → `#8b3a2a`
- Node background: `oklch(18% 0.010 250)` → `#ece6d8`
- Node border selected: `oklch(72% 0.12 95)` → `#3d6b4a`
- Node border default: `oklch(28% 0.010 250)` → `#d4c8b4`
- Node text color: `oklch(92% 0.008 250)` → `#2a2418`
- Edge stroke: `oklch(28% 0.010 250)` → `#d4c8b4`
- `colorMode="dark"` → `colorMode="light"`
- Background color: `oklch(22% 0.010 250)` → `#e0d8c8`

- [ ] **Step 3: Replace GraphView.module.css**

```css
.container { flex: 1; min-width: 0; height: 100%; }
.nodeLabel { display: flex; flex-direction: column; gap: 3px; padding: 2px; }
.nodeStatus { font-size: 10px; }
.nodeQuestion { font-family: var(--ff-ui); font-style: italic; font-size: 11px; font-weight: 400; line-height: 1.3; }
```

Change: `nodeQuestion` gains `font-style: italic`; `nodeStatus` drops `font-family: var(--ff-mono)` (redundant since `--ff-mono` is now Spectral anyway).

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /home/anselmlong/Projects/bonsai/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no output (no type changes, only runtime color string values changed).

- [ ] **Step 5: Commit**

```bash
cd /home/anselmlong/Projects/bonsai
git add frontend/components/GraphView.tsx frontend/components/GraphView.module.css
git commit -m "feat: redesign — parchment graph nodes, light mode React Flow"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Parchment palette tokens | Task 1 |
| Forest green accent replacing amber | Task 1 |
| Spectral serif as sole typeface | Task 1 (`--ff-mono` → Spectral) |
| No monospace font — spaced caps for labels | Tasks 4–8 (letter-spacing + text-transform) |
| Italic Spectral logo (home page) | Task 2 |
| Italic Spectral inputs | Task 3 |
| Italic Spectral logo (nav) | Task 4 |
| Spectral spaced caps toggles | Task 4 |
| Spectral italic tree labels | Task 5 |
| Tree panel parchment surface | Task 5 |
| Italic node title 18px | Task 6 |
| Green left-border on summary | Task 6 |
| Spaced caps badge/label | Task 6 |
| Parchment source cards, italic excerpt | Task 7 |
| Parchment status bar, spaced caps | Task 8 |
| GraphView parchment node colors | Task 9 |
| `colorMode="light"` on ReactFlow | Task 9 |
| Italic nodeQuestion in graph | Task 9 |

All spec requirements covered.

**Placeholder scan:** None found. Every task has complete CSS content.

**Type consistency:** No new types introduced. GraphView.tsx changes are runtime string values only — no interface changes.
