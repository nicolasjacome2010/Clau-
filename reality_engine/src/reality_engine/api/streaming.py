"""Turns a pipeline run into a stream of newline-delimited JSON.

NDJSON rather than SSE: the only consumer is Core API relaying to the
Flutter client, both of which parse JSON per line trivially, and SSE's
framing (`event:`/`data:`/`retry:`) would buy reconnection semantics that
are meaningless here — the work is not resumable, so a client that
reconnects has nothing to reconnect *to*. That is also the honest reason
this is a stream over one request rather than a WebSocket: the run lives
and dies with the request either way, and pretending otherwise would need
a queue and a worker (docs/ARCHITECTURE.md §2.2), not a different socket.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from pydantic import BaseModel

from reality_engine.pipeline.domain.events import PipelineEvent
from reality_engine.pipeline.orchestrator import SimulationPipeline, SimulationResult


class ResultEvent(BaseModel):
    """The last line of a successful stream."""

    type: str = "result"
    result: SimulationResult


class ErrorEvent(BaseModel):
    """The last line of a failed stream.

    A stream that simply stops is indistinguishable from a dropped
    connection, so a failure says so in-band before the body ends. The
    HTTP status is already 200 by the time the first line goes out —
    that's inherent to streaming, and the reason this event exists.
    """

    type: str = "error"
    message: str


async def stream_simulation(
    pipeline: SimulationPipeline, raw_input: str, declared_goals: list[str]
) -> AsyncIterator[str]:
    """Runs the pipeline, yielding one JSON line per event, result last.

    The run happens in its own task while this generator drains a queue,
    because the pipeline reports progress through a callback rather than by
    being a generator itself — that callback shape is what keeps
    `/v1/simulate` byte-for-byte unchanged for callers who don't care about
    progress.
    """
    queue: asyncio.Queue[PipelineEvent | None] = asyncio.Queue()

    async def on_stage(event: PipelineEvent) -> None:
        await queue.put(event)

    async def run() -> SimulationResult:
        try:
            return await pipeline.run(
                raw_input, declared_goals=declared_goals, on_stage=on_stage
            )
        finally:
            # Sentinel in `finally`, so a raising pipeline can't leave the
            # consumer below waiting on a queue nobody will ever fill.
            await queue.put(None)

    task = asyncio.create_task(run())

    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event.model_dump_json() + "\n"

        result = await task
    except Exception:
        # Broad on purpose, and safe: `asyncio.CancelledError` derives from
        # `BaseException`, so a client hanging up still cancels cleanly.
        # This generator is the last thing standing between a pipeline
        # failure and a truncated body that the client would read as a
        # dropped connection. The message stays generic — provider
        # internals are not the caller's business.
        task.cancel()
        yield ErrorEvent(message="La simulación no pudo completarse.").model_dump_json() + "\n"
        return

    yield ResultEvent(result=result).model_dump_json() + "\n"
