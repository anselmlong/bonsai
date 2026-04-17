from tavily import TavilyClient
from backend.models.types import ResearchConfig, Source


def search_tavily(question: str, config: ResearchConfig) -> list[Source]:
    """Call Tavily and return a list of Source objects."""
    client = TavilyClient()
    response = client.search(
        query=question,
        max_results=config.get("tavily_max_results", 5),
        include_answer=False,
    )
    return [
        Source(
            url=r.get("url", ""),
            title=r.get("title", ""),
            excerpt=r.get("content", "")[:500],
            score=r.get("score", 0.0),
        )
        for r in response.get("results", [])
    ]
