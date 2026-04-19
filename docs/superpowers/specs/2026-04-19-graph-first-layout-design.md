# Graph-First Layout with Summary Transition

**Date:** 2026-04-19
**Status:** Approved

## Overview

Move the graph view to the primary research page. While agents are searching, the graph expands in real time and fills the viewport. When synthesis completes, a banner prompts the user to view the summary. Clicking the banner fades the graph out and reveals a tabbed layout with Summary, Research Graph, and Tree tabs. Dive Deeper is removed entirely.

## State Machine

ResearchTree gains two new state variables replacing the old `view: "tree" | "graph"` toggle:

```
phase: "researching" | "banner" | "summary"
activeTab: "summary" | "graph" | "tree"
```

Transitions:
- Page load → `phase = "researching"` (graph is primary)
- `finalAnswer` arrives → `phase = "banner"` (banner overlays graph)
- User clicks banner → `phase = "summary"`, `activeTab = "summary"`

The `done` boolean from `useResearchStream` drives the `"researching" → "banner"` transition via a `useEffect` that watches `finalAnswer`.

## Layout by Phase

**`researching` and `banner` phases:**
- Full-viewport GraphView (no tab bar, no tree panel)
- Right detail panel (300px) shows the active node — click any node to inspect it
- Status bar at the bottom
- Nav: logo + query input only (TREE/GRAPH toggle removed)
- In `banner` phase: an absolutely-positioned banner at the bottom of the graph stage fades in, reading "Summary ready — view results" with a single dismiss button

**`summary` phase:**
- Tab bar appears below the nav: `Summary | Research Graph | Tree`
- All three tab panels are rendered in the DOM but only the active one is visible (`display: none` / `display: flex`) — no unmount, stream stays alive
- Default active tab: `summary`

## Animation

- **Banner fade-in:** `opacity: 0 → 1` over 300ms when `phase` transitions to `"banner"`
- **Graph → summary transition:** clicking the banner sets `phase = "summary"`. The graph stage and the tabbed layout are both absolutely positioned in a shared container during the transition. Graph fades out (`opacity: 1 → 0`, 400ms), tabbed layout fades in simultaneously. After transition, normal document flow resumes.
- Implementation: CSS `transition: opacity 400ms ease` + a short `transitionend` callback to clean up positioning. No animation library.

## Component Changes

### ResearchTree.tsx
- Remove `view` state
- Add `phase` and `activeTab` state
- `useEffect` on `finalAnswer`: when truthy, set `phase = "banner"`
- Remove `onDiveDeeper` handler and any dive-deeper related state
- Render graph-first layout for `researching`/`banner` phases
- Render tabbed layout for `summary` phase
- Remove TREE/GRAPH toggle buttons from nav

### NodeDetail.tsx
- Remove Dive Deeper button and `onDiveDeeper` prop

### ResearchTree.module.css
- Add: `.banner`, `.bannerBtn`, `.tabBar`, `.tabBtn`, `.tabBtnActive`, `.tabPanel`, `.fadeOut`, `.fadeIn`

### backend/main.py
- Remove `DiveDeeperRequest` model
- Remove `POST /research/{jobId}/dive-deeper` endpoint

### Unchanged
- `GraphView.tsx` — no changes
- `TreePanel.tsx` — no changes
- `AnswerRenderer.tsx` — no changes
- `useResearchStream.ts` — no changes
- `useResearchTree.ts` — no changes
- `StatusBar.tsx` — no changes

## What Is Removed

- The TREE/GRAPH toggle in the nav bar
- The Dive Deeper button in NodeDetail
- The `POST /research/{jobId}/dive-deeper` backend endpoint
- The `DiveDeeperRequest` Pydantic model
- The `view` state in ResearchTree

## Out of Scope

- Animating individual graph nodes as they appear (existing behavior unchanged)
- Persisting the selected tab across sessions
- Mobile/responsive layout adjustments
