from unittest.mock import MagicMock, patch
from backend.agents.nodes.searcher import search_tavily
from backend.models.types import DEFAULT_CONFIG
import json
import hashlib
from pathlib import Path
import backend.agents.nodes.searcher as searcher_module


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
    assert len(sources) == 1
    assert sources[0]["url"] == "https://a.com"


@patch("backend.agents.nodes.searcher.TavilyClient")
def test_cache_hit_skips_api(mock_client_class, tmp_path, monkeypatch):
    monkeypatch.setattr(searcher_module, "CACHE_DIR", tmp_path / "search")
    (tmp_path / "search").mkdir(parents=True)

    # Pre-populate cache
    max_results = DEFAULT_CONFIG["tavily_max_results"]
    key = hashlib.sha256(f"cached query{max_results}".encode()).hexdigest()[:16]
    cache_file = tmp_path / "search" / f"{key}.json"
    cached_sources = [{"url": "https://cached.com", "title": "Cached", "excerpt": "hit", "score": 1.0}]
    cache_file.write_text(json.dumps({"query": "cached query", "max_results": max_results, "results": cached_sources}))

    sources = search_tavily("cached query", DEFAULT_CONFIG)

    mock_client_class.assert_not_called()
    assert sources[0]["url"] == "https://cached.com"


@patch("backend.agents.nodes.searcher.TavilyClient")
def test_corrupt_cache_treated_as_miss(mock_client_class, tmp_path, monkeypatch):
    monkeypatch.setattr(searcher_module, "CACHE_DIR", tmp_path / "search")
    (tmp_path / "search").mkdir(parents=True)

    max_results = DEFAULT_CONFIG["tavily_max_results"]
    key = hashlib.sha256(f"corrupt query{max_results}".encode()).hexdigest()[:16]
    (tmp_path / "search" / f"{key}.json").write_text("not valid json{{")

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.search.return_value = {"results": []}

    sources = search_tavily("corrupt query", DEFAULT_CONFIG)

    mock_client.search.assert_called_once()
    assert sources == []
