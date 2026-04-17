# Bonsai Visual Redesign — Design Spec
**Design Spec · 2026-04-17**

## Overview

A full visual overhaul from the current dark developer-tool aesthetic to a light editorial/parchment theme. Inspired by academic journals, naturalist field notes, and archival research documents. The redesign touches every CSS file in the frontend — no new components, no layout changes, no new routes.

---

## Design Direction

**Theme:** Light parchment — warm off-white background, ink-on-paper text, aged-paper surface tones.

**Accent:** Forest green (`#3d6b4a`) — botanical, grounds the bonsai name, reads clearly on parchment without feeling digital.

**Typography:** Spectral serif throughout. Italic for titles, logo, node labels, and placeholder text. Upright for body copy. **No monospace font** — Azeret Mono is removed entirely. Labels, metadata, and status text use Spectral with wide letter-spacing and `text-transform: uppercase` to create typographic contrast without changing the font family.

---

## Design Tokens (globals.css)

Replace the current dark token set with:

```css
/* Palette */
--bg:         #f5f0e8;   /* parchment page */
--surface:    #ece6d8;   /* slightly darker parchment (panels, nav) */
--surface-2:  #e0d8c8;   /* hover states, inset areas */
--border:     #d4c8b4;   /* primary border */
--border-2:   #c0b8a8;   /* secondary border, separators */

/* Text */
--text:       #2a2418;   /* deep ink — primary */
--text-2:     #5a5040;   /* secondary body copy */
--text-3:     #a89e88;   /* labels, metadata, placeholders */

/* Accent */
--amber:      #3d6b4a;   /* forest green — replaces amber everywhere */
--amber-dim:  rgba(61, 107, 74, 0.12);
--amber-dim2: rgba(61, 107, 74, 0.06);

/* Status (unchanged semantics, updated values) */
--green:      #3d6b4a;   /* same as accent */
--red:        #8b3a2a;   /* muted terracotta red */

/* Typography */
--ff-ui:      'Spectral', Georgia, serif;
--ff-body:    'Spectral', Georgia, serif;
--ff-mono:    'Spectral', Georgia, serif;  /* mono is replaced — all Spectral */
```

**Font import:** Remove Bricolage Grotesque and Azeret Mono. Keep only Spectral with weights 300, 400, 500 and italic variants:

```css
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,400;0,500;1,300;1,400;1,500&display=swap');
```

---

## Component Changes

All changes are CSS only unless noted. No TypeScript/JSX changes required.

### `frontend/app/page.module.css` — Home Page

- Background: `var(--bg)`
- Logo: Spectral italic, 48px, `letter-spacing: -.02em`
- Logo "o": forest green accent
- Subheading: Spectral, 10px, `letter-spacing: .1em`, `text-transform: uppercase`, `color: var(--text-3)`
- Search input: `background: var(--surface)`, italic Spectral placeholder, `border: 1px solid var(--border)`
- Submit button: `background: var(--amber)` (solid green fill), `color: var(--bg)`, no border

### `frontend/components/QueryInput.module.css` — Search Input

- Hero input: Spectral italic, parchment surface background, border matches `var(--border)`
- Hero button: solid green fill (`var(--amber)`), parchment text (`var(--bg)`)
- Nav input: transparent background, Spectral italic, `border: 1px solid var(--border)`
- Nav button: transparent, Spectral spaced caps, `color: var(--text-3)`, hover → green border + green text

### `frontend/components/ResearchTree.module.css` — Shell + Nav

- `.shell`: `background: var(--bg)`
- `.nav`: `background: var(--surface)`, `border-bottom: 1px solid var(--border)`, height 44px
- `.logo`: Spectral italic, 16px, `color: var(--text)`, green "o"
- `.toggleBtn`: Spectral, 9px, `letter-spacing: .16em`, `text-transform: uppercase`, `color: var(--text-3)`
- `.toggleBtn.active`: `background: var(--bg)`, `border-color: var(--border)`, `color: var(--text)`
- `.answerText`: Spectral, 14px weight 300, `color: var(--text-2)`, `line-height: 1.85`
- `.graphDetailPane`: `border-left: 1px solid var(--border)` (no change needed, inherits tokens)

### `frontend/components/TreePanel.module.css` — Research Tree Panel

- `.panel`: `background: var(--surface)`, `border-right: 1px solid var(--border)`, width 220px
- `.header`: Spectral, 8px, `letter-spacing: .18em`, `text-transform: uppercase`, `color: var(--text-3)`
- `.row:hover`: `background: var(--surface-2)`
- `.selected`: `background: var(--amber-dim2)`
- `.selected .label`: `color: var(--amber)`
- `.label`: Spectral italic, 12px, `color: var(--text-2)`
- `.meta`: Spectral, 9px, `letter-spacing: .06em`, `color: var(--text-3)`
- `.children`: `border-left: 1px solid var(--border)`, indent unchanged
- Status colors: `.complete` → `var(--green)`, `.searching/.reflecting/.spawning` → `var(--amber)` at 60% opacity, `.pending` → `var(--text-3)`
- Scrollbar: track `var(--surface-2)`, thumb `var(--border-2)`, hover `var(--amber)`

### `frontend/components/NodeDetail.module.css` — Detail Panel

- `.panel`: `background: var(--bg)`, padding 20px 24px
- `.badge`: Spectral, 8px, `letter-spacing: .18em`, `text-transform: uppercase`, `color: var(--green)`
- `.title`: Spectral italic, 18px, `color: var(--text)`, `line-height: 1.3`
- `.diveBtn`: Spectral, 9px, `letter-spacing: .12em`, `text-transform: uppercase`, `border: 1px solid var(--amber)`, `color: var(--amber)`, transparent background
- `.label`: Spectral, 8px, `letter-spacing: .18em`, `text-transform: uppercase`, `color: var(--text-3)`
- `.summary`: Spectral weight 300, 13px, `color: var(--text-2)`, `line-height: 1.85`, `border-left: 2px solid var(--amber-dim)`, `padding-left: 14px` — replaces the current surface-background box

### `frontend/components/SourceCard.module.css` — Source Cards

- `.card`: `background: var(--surface)`, `border: 1px solid var(--border)`
- `.card:hover`: `border-color: var(--border-2)`
- `.domain`: Spectral, 9px, `letter-spacing: .1em`, `text-transform: uppercase`, `color: var(--amber)`
- `.score`: Spectral, 9px, `letter-spacing: .06em`, `color: var(--green)`
- `.title`: Spectral, 12px weight 400, `color: var(--text-2)`
- `.excerpt`: Spectral italic weight 300, 11px, `color: var(--text-3)`, `line-height: 1.65`

### `frontend/components/StatusBar.module.css` — Bottom Bar

- `.bar`: `background: var(--surface)`, `border-top: 1px solid var(--border)`, height 30px
- All text: Spectral, 9px, `letter-spacing: .1em`, `text-transform: uppercase`, `color: var(--text-3)`
- `.dot`: `background: var(--amber)` (green dot)
- `.active`: `color: var(--text-2)`
- `.done`: `color: var(--green)`
- `.trace`: `color: var(--amber)`

### `frontend/components/GraphView.tsx` + `GraphView.module.css` — Graph Nodes

Node inline styles in `GraphView.tsx` must be updated (they are hardcoded `oklch` values):
- Node background: `#ece6d8` (surface)
- Node border: selected → `#3d6b4a`, default → `#d4c8b4`
- Node text: `#2a2418`
- Node label font: `Spectral, Georgia, serif`, italic

---

## Files Changed

| File | Change |
|---|---|
| `frontend/app/globals.css` | Rewrite tokens, replace font import |
| `frontend/app/page.module.css` | Parchment home page styles |
| `frontend/components/QueryInput.module.css` | Light input variants |
| `frontend/components/ResearchTree.module.css` | Parchment shell + nav |
| `frontend/components/TreePanel.module.css` | Parchment tree panel |
| `frontend/components/NodeDetail.module.css` | Editorial detail panel |
| `frontend/components/SourceCard.module.css` | Parchment source cards |
| `frontend/components/StatusBar.module.css` | Parchment status bar |
| `frontend/components/GraphView.tsx` | Update hardcoded node colors |
| `frontend/components/GraphView.module.css` | Graph container background |

---

## Not In Scope

- Layout changes (panel widths, component structure)
- New components or routes
- Backend changes
- Animation changes (pulse keyframe timing unchanged)
- Dark mode toggle (single theme only)

---

## Testing

| Area | How to verify |
|---|---|
| Home page | `localhost:3000` — parchment background, italic logo, green submit button, no monospace |
| Research tree | Run a query — tree panel shows serif italic labels, node detail has green left-border on summary |
| Graph view | Switch to graph — nodes render in parchment palette, clicking opens NodeDetail in matching theme |
| Status indicators | Active branch shows green dot/label; complete shows green ✓; pending shows muted text |
| Source cards | Cards show domain in green spaced caps, excerpt in italic |
| Scrollbar | Tree panel scrollbar matches parchment theme |
