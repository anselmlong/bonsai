import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.main import _jobs, MAX_ACTIVE_JOBS, MAX_RETAINED_JOBS


@pytest.mark.parametrize("payload", [
    {"query": " "}, {"query": "x" * 4001},
    {"query": "test", "config": {"max_branches": 100}},
    {"query": "test", "config": {"max_depth": -1}},
    {"query": "test", "config": {"planner_model": "unapproved"}},
])
async def test_invalid_workload_rejected(client, payload):
    response = await client.post("/research", json=payload)
    assert response.status_code == 422


async def test_concurrency_is_bounded(client, monkeypatch):
    monkeypatch.setattr("backend.main._jobs", {str(i): {"status": "running"} for i in range(MAX_ACTIVE_JOBS)})
    with patch("backend.main.run_research", new_callable=AsyncMock) as run:
        assert (await client.post("/research", json={"query": "test"})).status_code == 429
        run.assert_not_called()


async def test_failure_releases_capacity_and_terminates_stream(client, monkeypatch):
    jobs = {}
    monkeypatch.setattr("backend.main._jobs", jobs)
    with patch("backend.main.run_research", new_callable=AsyncMock, side_effect=RuntimeError("private backend error")):
        response = await client.post("/research", json={"query": "test"})
        job_id = response.json()["job_id"]
        await jobs[job_id]["task"]
        assert (await client.get(f"/research/{job_id}/result")).json() == {"status": "failed"}
        stream = await client.get(f"/research/{job_id}/stream")
        assert "Research failed" in stream.text
        assert "private backend error" not in stream.text


async def test_old_completed_jobs_evicted(client, monkeypatch):
    jobs = {str(i): {"status": "complete"} for i in range(MAX_RETAINED_JOBS)}
    monkeypatch.setattr("backend.main._jobs", jobs)
    with patch("backend.main.run_research", new_callable=AsyncMock, return_value={"final_answer": "done"}):
        response = await client.post("/research", json={"query": "test"})
        await jobs[response.json()["job_id"]]["task"]
    assert len(jobs) == MAX_RETAINED_JOBS
    assert "0" not in jobs


async def test_success_closes_stream_without_provider_sentinel(client, monkeypatch):
    jobs = {}
    monkeypatch.setattr("backend.main._jobs", jobs)
    with patch("backend.main.run_research", new_callable=AsyncMock, return_value={"final_answer": "done"}):
        response = await client.post("/research", json={"query": "test"})
        job_id = response.json()["job_id"]
        await jobs[job_id]["task"]
    assert jobs[job_id]["status"] == "complete"
    assert await asyncio.wait_for(jobs[job_id]["queue"].get(), timeout=1) is None
    assert (await client.get(f"/research/{job_id}/result")).json()["final_answer"] == "done"
