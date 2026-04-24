# Eval Search Cache Design

**Date:** 2026-04-25  
**Goal:** Cache Tavily/Brave search results to disk so eval runs are deterministic and cheap enough for autoresearch-style agent iteration overnight.

---

## Problem

`scripts/eval.py` calls `run_research` which hits Tavily/Brave on every run. This causes two issues:
1. **Non-determinism** — search results vary run-to-run, making it impossible to tell if an agent improvement is real or noise.
2. **Cost** — every eval experiment burns API credits. Autoresearch needs ~100 experiments overnight; that's prohibitive without caching.

---

## Solution

Modify `search_tavily` in `backend/agents/nodes/searcher.py` to check a disk cache before making any API call. On a cache miss, call the API as today and write the result to disk. Always-on: no flags or config needed.

---

## Cache Storage

- **Location:** `cache/search/` at the repo root
- **File per entry:** `cache/search/<hash>.json` where `<hash>` is the first 16 hex characters of `SHA256(query + str(max_results))`
- **File format:**
  ```json
  {
    "query": "...",
    "max_results": 5,
    "results": [
      { "url": "...", "title": "...", "excerpt": "...", "score": 0.9 }
    ]
  }
  ```
- **TTL:** None — entries are permanent until manually deleted
- **Git:** `cache/` is added to `.gitignore`

---

## Code Change

Only `backend/agents/nodes/searcher.py` changes.

Add a module-level constant:
```python
CACHE_DIR = Path("cache/search")
```

Add a private helper:
```python
def _cache_path(query: str, max_results: int) -> Path | None
```
Returns the path for this query's cache file, or `None` if the cache dir can't be created (silent failure).

Modify `search_tavily` to:
1. Call `_cache_path` — if `None`, skip caching entirely
2. If the cache file exists and is valid JSON, deserialize and return immediately
3. Otherwise call Tavily (with Brave fallback) as today
4. Write the result to the cache file before returning

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Cache dir creation fails | Log warning, skip cache, proceed with live call |
| Cache file is corrupt/unreadable | Log warning, treat as miss, overwrite on return |
| Cache write fails (disk full, permissions) | Log warning, return results normally |
| Tavily returns empty results | Cache them — avoids re-hitting API for dead queries |

All cache failures are non-fatal and silent to callers.

---

## Out of Scope

- Caching LLM calls (planner, synthesizer, reflect)
- Cache TTL or invalidation strategies
- Per-caller opt-in/opt-out flags
- Distributed or shared cache
