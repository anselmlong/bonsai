from unittest.mock import MagicMock, patch
from backend.agents.nodes.searcher import search_tavily
from backend.models.types import DEFAULT_CONFIG


@patch("backend.agents.nodes.searcher.TavilyClient")
def test_search_tavily_returns_sources(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {
        "results": [
            {"url": "https://example.com", "title": "Example", "content": "Some content here.", "score": 0.92},
            {"url": "https://other.com", "title": "Other", "content": "More content.", "score": 0.85},
        ]
    }

    sources = search_tavily("What causes climate change?", DEFAULT_CONFIG)

    assert len(sources) == 2
    assert sources[0]["url"] == "https://example.com"
    assert sources[0]["score"] == 0.92
    assert len(sources[0]["excerpt"]) <= 500
    mock_client.search.assert_called_once_with(
        query="What causes climate change?",
        max_results=DEFAULT_CONFIG["tavily_max_results"],
        include_answer=False,
    )


@patch("backend.agents.nodes.searcher.TavilyClient")
def test_search_tavily_handles_missing_fields(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {
        "results": [{"url": "https://example.com"}]
    }

    sources = search_tavily("test query", DEFAULT_CONFIG)

    assert sources[0]["title"] == ""
    assert sources[0]["excerpt"] == ""
    assert sources[0]["score"] == 0.0
