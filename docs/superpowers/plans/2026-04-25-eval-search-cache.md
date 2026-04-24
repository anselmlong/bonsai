# Eval Search Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cache Tavily/Brave search results to disk so eval runs are deterministic and cheap enough for autoresearch-style agent iteration overnight.

**Architecture:** Modify `search_tavily` in `searcher.py` to check a SHA256-keyed JSON file in `cache/search/` before making any API call. On a miss, call the API and write the result to disk. All cache failures are non-fatal and silent to callers.

**Tech Stack:** Python `hashlib` (stdlib), `pathlib` (stdlib), `json` (stdlib)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/agents/nodes/searcher.py` | Modify | Add `CACHE_DIR`, `_cache_path`, cache read/write in `search_tavily` |
| `backend/tests/test_searcher.py` | Modify | Add tests for cache hit, miss, corrupt file, write failure |
| `.gitignore` | Modify | Add `cache/` entry |

---

### Task 1: Gitignore the cache directory

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `cache/` to `.gitignore`**

Open `.gitignore` and append one line:

```
cache/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore cache directory"
```

---

### Task 2: Write failing tests for cache behaviour

**Files:**
- Modify: `backend/tests/test_searcher.py`

- [ ] **Step 1: Add imports at the top of `test_searcher.py`**

Add after the existing imports:

```python
import json
import tempfile
from pathlib import Path
import backend.agents.nodes.searcher as searcher_module
```

- [ ] **Step 2: Write test — cache miss calls API and writes to disk**

```python
@patch("backend.agents.nodes.searcher.TavilyClient")
def test_cache_miss_calls_api_and_writes(mock_client_class, tmp_path, monkeypatch):
    monkeypatch.setattr(searcher_module, "CACHE_DIR", tmp_path / "search")
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {
        "results": [{"url": "https://a.com", "title": "A", "content": "text", "score": 0.9}]
    }

    sources = search_tavily("cache miss query", DEFAULT_CONFIG)

    mock_client.search.assert_called_once()
    cache_files = list((tmp_path / "search").glob("*.json"))
    assert len(cache_files) == 1
    data = json.loads(cache_files[0].read_text())
    assert data["query"] == "cache miss query"
    assert len(data["results"]) == 1
```

- [ ] **Step 3: Write test — cache hit skips API call**

```python
@patch("backend.agents.nodes.searcher.TavilyClient")
def test_cache_hit_skips_api(mock_client_class, tmp_path, monkeypatch):
    monkeypatch.setattr(searcher_module, "CACHE_DIR", tmp_path / "search")
    (tmp_path / "search").mkdir(parents=True)

    # Pre-populate cache
    import hashlib
    max_results = DEFAULT_CONFIG["tavily_max_results"]
    key = hashlib.sha256(f"cached query{max_results}".encode()).hexdigest()[:16]
    cache_file = tmp_path / "search" / f"{key}.json"
    cached_sources = [{"url": "https://cached.com", "title": "Cached", "excerpt": "hit", "score": 1.0}]
    cache_file.write_text(json.dumps({"query": "cached query", "max_results": max_results, "results": cached_sources}))

    sources = search_tavily("cached query", DEFAULT_CONFIG)

    mock_client_class.assert_not_called()
    assert sources[0]["url"] == "https://cached.com"
```

- [ ] **Step 4: Write test — corrupt cache file is treated as miss**

```python
@patch("backend.agents.nodes.searcher.TavilyClient")
def test_corrupt_cache_treated_as_miss(mock_client_class, tmp_path, monkeypatch):
    monkeypatch.setattr(searcher_module, "CACHE_DIR", tmp_path / "search")
    (tmp_path / "search").mkdir(parents=True)

    import hashlib
    max_results = DEFAULT_CONFIG["tavily_max_results"]
    key = hashlib.sha256(f"corrupt query{max_results}".encode()).hexdigest()[:16]
    (tmp_path / "search" / f"{key}.json").write_text("not valid json{{")

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {"results": []}

    sources = search_tavily("corrupt query", DEFAULT_CONFIG)

    mock_client.search.assert_called_once()
```

- [ ] **Step 5: Run tests to verify they all fail**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_searcher.py -v
```

Expected: the 3 new tests FAIL (cache logic not implemented yet), existing 2 tests PASS.

- [ ] **Step 6: Commit failing tests**

```bash
git add backend/tests/test_searcher.py
git commit -m "test: add failing tests for search disk cache"
```

---

### Task 3: Implement cache in `searcher.py`

**Files:**
- Modify: `backend/agents/nodes/searcher.py`

- [ ] **Step 1: Add imports and `CACHE_DIR` constant**

At the top of `searcher.py`, add after the existing imports:

```python
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path("cache/search")
```

- [ ] **Step 2: Add `_cache_path` helper**

Add after the `CACHE_DIR` constant, before `_search_brave`:

```python
def _cache_path(query: str, max_results: int) -> Path | None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning(f"Search cache dir unavailable: {e}")
        return None
    key = hashlib.sha256(f"{query}{max_results}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"
```

- [ ] **Step 3: Modify `search_tavily` to read from and write to cache**

Replace the existing `search_tavily` function with:

```python
def search_tavily(question: str, config: ResearchConfig) -> list[Source]:
    """Call Tavily, fallback to Brave on failure. Results are cached to disk."""
    max_results = config.get("tavily_max_results", 5)
    path = _cache_path(question, max_results)

    if path is not None and path.exists():
        try:
            data = json.loads(path.read_text())
            return [Source(**r) for r in data["results"]]
        except Exception as e:
            logger.warning(f"Search cache read failed: {e}")

    results: list[Source] = []
    try:
        client = TavilyClient()
        response = client.search(
            query=question,
            max_results=max_results,
            include_answer=False,
        )
        results = [
            Source(
                url=r.get("url", ""),
                title=r.get("title", ""),
                excerpt=r.get("content", ""),
                score=r.get("score", 0.0),
            )
            for r in response.get("results", [])
        ]
    except Exception as e:
        logger.warning(f"Tavily failed: {e}, falling back to Brave")
        try:
            results = _search_brave(question, max_results)
        except Exception as e:
            logger.error(f"Brave fallback failed: {e}")

    if path is not None:
        try:
            path.write_text(json.dumps({
                "query": question,
                "max_results": max_results,
                "results": list(results),
            }))
        except Exception as e:
            logger.warning(f"Search cache write failed: {e}")

    return results
```

- [ ] **Step 4: Run all searcher tests**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/test_searcher.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit implementation**

```bash
git add backend/agents/nodes/searcher.py
git commit -m "feat: cache search results to disk for deterministic eval runs"
```

---

### Task 4: Smoke test the cache end-to-end

**Files:** none (manual verification)

- [ ] **Step 1: Run the full test suite to check for regressions**

```bash
cd /home/anselmlong/Projects/bonsai && uv run pytest backend/tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Verify cache files are created on a real search call**

```bash
cd /home/anselmlong/Projects/bonsai && python -c "
from backend.agents.nodes.searcher import search_tavily
from backend.models.types import DEFAULT_CONFIG
results = search_tavily('what is the capital of France', DEFAULT_CONFIG)
print(f'Results: {len(results)}')
import os; files = os.listdir('cache/search') if os.path.exists('cache/search') else []
print(f'Cache files: {len(files)}')
"
```

Expected output:
```
Results: 5
Cache files: 1
```

- [ ] **Step 3: Run the same query again and verify no API call is made (cache hit)**

```bash
cd /home/anselmlong/Projects/bonsai && python -c "
from backend.agents.nodes.searcher import search_tavily
from backend.models.types import DEFAULT_CONFIG
import time
start = time.time()
results = search_tavily('what is the capital of France', DEFAULT_CONFIG)
elapsed = time.time() - start
print(f'Results: {len(results)}, Time: {elapsed:.2f}s')
"
```

Expected: time is < 0.1s (cache hit, no network call).
