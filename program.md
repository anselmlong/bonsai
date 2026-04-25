# Bonsai Autoresearch Program

## What You're Optimizing

You are improving `experiment.py`, a self-contained research agent pipeline that answers
factual questions. Edit this file to improve the composite score on SimpleQA.

**Eval command:**
    uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json

**Metric:** weighted composite score (higher is better)
- factual_accuracy  × 0.50
- completeness      × 0.20
- citation_accuracy × 0.20
- source_quality    × 0.05
- conciseness       × 0.05

**Baseline composite score:** 0.904 (18/20 correct) — established 2026-04-25, Brave fallback active

> Tavily is rate-limited (free plan exhausted). Brave API is the active search provider.
> Cache is fully warmed (172 entries). Subsequent runs are cache-served and free.

## Current Architecture

```
query
  → plan_research()     — LLM decomposes into sub-questions (PLANNER_PROMPT)
  → BranchProcessor     — each sub-question fans out in parallel:
      → search()        — Tavily web search (disk-cached)
      → reflect_on_results()  — LLM decides quality / whether to recurse (REFLECT_PROMPT)
      → [recursive sub-branches if needed]
  → synthesize_answer() — LLM combines all branches into final answer (SYNTHESIZER_PROMPT)
```

All prompts (`PLANNER_PROMPT`, `REFLECT_PROMPT`, `SYNTHESIZER_PROMPT`) are inline strings.
All logic is in this one file. Edit freely.

## Research Directions

### Primary: Search Before Planning

**Hypothesis:** The planner currently operates blind — it sees only the raw query, no web
content. If we run an initial `search(query, config)` first and pass those results to
`plan_research`, the planner can generate better-targeted sub-questions grounded in
what's actually on the web.

**What to try:**
1. In `run_research`, call `search(query, config)` before `plan_research`
2. Pass the search results as additional context in the `HumanMessage` inside `plan_research`
3. Update `PLANNER_PROMPT` to instruct the planner to use the initial search context

**Expected benefit:** Fewer redundant sub-questions, better coverage of what's actually
findable, higher factual accuracy and completeness.

### Secondary: Planner Prompt Tuning

- Try stricter scaling rules: bias toward 1 sub-question for simple fact queries
- Require sub-questions to mention key named entities from the original query
- Add a "what is still unknown after a quick web search?" framing

### Secondary: Reflect Conservatism

- Default recurses when there are "genuine gaps" — try raising the bar
- Try: only recurse if fewer than 2 sources were found on the first search
- Try: remove recursion entirely for max_depth=1 evals and see if it helps

### Secondary: Synthesizer Prompt Tuning

- Try a shorter, more direct output style focused on factual density
- Try instructing the synthesizer to always state confidence level on key claims
- Try requiring citations on every sentence that states a fact

## Eval validity requirements

Before results are trustworthy:
1. **Search provider** — `search()` tries Tavily first, falls back to Brave. Brave API key is in
   `.env`. If both fail, sources will be empty and scores will drop.
2. **Warm cache** — run baseline once to populate `cache/search/` (currently 172 entries). All
   subsequent runs are cache-served and free.
3. **Deterministic planner** — `plan_research()` uses `temperature=0`. This ensures the same
   sub-questions each run, keeping cache hits stable. If you change the planner prompt or model,
   delete `cache/search/` and re-run baseline to warm the new sub-questions.

## Workflow

For each experiment:
1. Make ONE focused change to `experiment.py`
2. Run: `uv run python scripts/eval.py --experiment --n 20 --output results/experiment.json`
3. Read the composite score from the output
4. If composite > baseline:
   - `git add experiment.py && git commit -m "experiment: <description> (composite: X.XXX)"`
   - Update baseline to new score
5. If composite <= baseline:
   - `git checkout experiment.py`
   - Try the next direction

## Rules

- **Only edit `experiment.py`** — do not touch eval.py, backend/, scripts/, or any other file
- **One change at a time** — don't compound multiple changes before testing
- **Commit improvements** — git history is your experiment log
- **Revert failures** — use `git checkout experiment.py` to restore the last working version
