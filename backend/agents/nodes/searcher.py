import os
import logging
import hashlib
import json
import requests
from pathlib import Path
from tavily import TavilyClient
from backend.models.types import ResearchConfig, Source

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "cache" / "search"


def _cache_path(query: str, max_results: int) -> Path:
    key = hashlib.sha256(f"{query}{max_results}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def _search_brave(question: str, max_results: int) -> list[Source]:
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        raise ValueError("BRAVE_API_KEY not set")

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"X-Subscription-Token": api_key}
    params = {"q": question, "count": max_results}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    return [
        Source(
            url=r.get("url", ""),
            title=r.get("title", ""),
            excerpt=r.get("snippet", ""),
            score=1.0,
        )
        for r in data.get("web", {}).get("results", [])
    ]


def search_tavily(question: str, config: ResearchConfig) -> list[Source]:
    """Call Tavily, fallback to Brave on failure. Results are cached to disk."""
    max_results = config.get("tavily_max_results", 5)
    path = _cache_path(question, max_results)

    if path.exists():
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

    if results:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "query": question,
                "max_results": max_results,
                "results": [dict(r) for r in results],
            }))
        except Exception as e:
            logger.warning(f"Search cache write failed: {e}")

    return results
