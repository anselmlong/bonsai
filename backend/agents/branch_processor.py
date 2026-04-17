import asyncio
import time
import uuid
from backend.models.types import (
    BranchResult, NodeEvent, ResearchConfig, Source,
)
from backend.agents.nodes.searcher import search_tavily
from backend.agents.nodes.reflect import reflect_on_results


class BranchProcessor:
    """Handles one research branch: search → reflect → optional recursive sub-branches.

    Pushes NodeEvents to the shared queue. Returns a BranchResult.
    """

    def __init__(self, event_queue: asyncio.Queue) -> None:
        self._queue = event_queue

    async def run(
        self,
        question: str,
        parent_id: str | None,
        depth: int,
        config: ResearchConfig,
        parent_summary: str | None,
    ) -> BranchResult:
        node_id = uuid.uuid4().hex[:8]
        max_depth = config.get("max_depth", 2)

        await self._emit(NodeEvent(
            type="branch_started", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))

        # Search
        await self._emit(NodeEvent(
            type="branch_searching", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))
        sources = await asyncio.to_thread(search_tavily, question, config)

        # Reflect
        await self._emit(NodeEvent(
            type="branch_reflecting", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=None, summary=None,
            answer=None, timestamp=time.time(),
        ))
        reflect = await asyncio.to_thread(
            reflect_on_results, question, sources, depth, parent_summary, config
        )

        # Recursive sub-branches (only if below max depth)
        sub_branches: list[BranchResult] = []
        if reflect.should_recurse and depth < max_depth and reflect.sub_questions:
            await self._emit(NodeEvent(
                type="branch_spawning", node_id=node_id, parent_id=parent_id,
                depth=depth, question=question, sources=None, summary=None,
                answer=None, timestamp=time.time(),
            ))
            tasks = [
                self.run(
                    question=q,
                    parent_id=node_id,
                    depth=depth + 1,
                    config=config,
                    parent_summary=reflect.summary,
                )
                for q in reflect.sub_questions
            ]
            sub_branches = list(await asyncio.gather(*tasks))

        await self._emit(NodeEvent(
            type="branch_complete", node_id=node_id, parent_id=parent_id,
            depth=depth, question=question, sources=sources,
            summary=reflect.summary, answer=None, timestamp=time.time(),
        ))

        return BranchResult(
            node_id=node_id,
            question=question,
            summary=reflect.summary,
            sources=sources,
            depth=depth,
            sub_branches=sub_branches,
        )

    async def _emit(self, event: NodeEvent) -> None:
        await self._queue.put(event)
