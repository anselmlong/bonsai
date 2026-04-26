import os
import logging
import requests
from tavily import TavilyClient
from backend.models.types import ResearchConfig, Source

logger = logging.getLogger(__name__)


def _search_serper(question: str, max_results: int) -> list[Source]:
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        return []
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": question, "num": max_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return [
        Source(
            url=r.get("link", ""),
            title=r.get("title", ""),
            excerpt=r.get("snippet", ""),
            score=0.0,
        )
        for r in data.get("organic", [])[:max_results]
    ]


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
    """Search via Serper → Tavily → Brave fallback chain."""
    max_results = config.get("tavily_max_results", 5)

    serper_results = _search_serper(question, max_results)
    if serper_results:
        return serper_results

    try:
        client = TavilyClient()
        response = client.search(
            query=question,
            max_results=max_results,
            include_answer=False,
        )
        return [
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
        return _search_brave(question, max_results)
    except Exception as e:
        logger.error(f"Brave fallback failed: {e}")
        return []
