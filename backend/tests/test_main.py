import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_post_research_returns_job_id(client):
    response = await client.post("/research", json={"query": "What is X?"})
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str)


@pytest.mark.asyncio
@patch("backend.main.run_research", new_callable=AsyncMock)
async def test_stream_delivers_events(mock_run, client):
    async def fake_run(job_id, query, config, event_queue):
        import time
        await event_queue.put({
            "type": "research_started", "node_id": "root", "parent_id": None,
            "depth": 0, "question": query, "sources": None, "summary": None,
            "answer": None, "timestamp": time.time(),
        })
        await event_queue.put(None)  # sentinel
        return {"branches": [], "final_answer": "done"}

    mock_run.side_effect = fake_run

    post_resp = await client.post("/research", json={"query": "Test?"})
    job_id = post_resp.json()["job_id"]

    async with client.stream("GET", f"/research/{job_id}/stream") as stream:
        lines = []
        async for line in stream.aiter_lines():
            if line.startswith("data:"):
                lines.append(line)
            if any("research_started" in l for l in lines):
                break

    assert any("research_started" in l for l in lines)
