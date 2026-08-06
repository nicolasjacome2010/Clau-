"""Progress events emitted while a pipeline runs.

docs/UX_DESIGN.md Pantalla 6 lights up each stage as it completes, which
needs the pipeline to say something *while* it works rather than only at
the end. These are that vocabulary.

The stage ids are per **agent**, not per UI row: what is actually running
is an agent, and collapsing twelve of them into the spec's six labels here
would bake display copy into the engine. The client groups and labels them
(docs/UX_DESIGN.md is the owner of those words), and a new agent shows up
as a new id rather than silently disappearing into someone else's bucket.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel


class PipelineStage(StrEnum):
    SAFETY_GATE = "safety_gate"
    COMPREHENSION = "comprehension"
    SUMMARY = "summary"
    GOALS_EXTRACTION = "goals_extraction"
    EMOTIONS = "emotions"
    PSYCHOLOGY = "psychology"
    RISK_ANALYSIS = "risk_analysis"
    SCENARIO_GENERATION = "scenario_generation"
    COMPARISON = "comparison"
    RANKING = "ranking"
    SYNTHESIS = "synthesis"
    MEMORY = "memory"


class StageEvent(BaseModel):
    """One agent started, or finished.

    Both edges are emitted, not just completions: a client that only heard
    about finished stages would have nothing to show as "in progress",
    which is the whole point of the screen.
    """

    type: Literal["stage"] = "stage"
    stage: PipelineStage
    status: Literal["started", "completed"]


class HaltedEvent(BaseModel):
    """The Safety Gate stopped the run (docs/REALITY_ENGINE.md §1).

    Its own event rather than a stage status, because the stream ends here
    and the client must render a referral instead of a result — a listener
    that treated it as "one more completed stage" would sit waiting for
    scenarios that are never coming.
    """

    type: Literal["halted"] = "halted"


PipelineEvent: TypeAlias = StageEvent | HaltedEvent

#: What a caller passes in to hear about progress. Optional everywhere: a
#: pipeline that nobody is watching must behave exactly as it did before
#: this existed, which is what keeps `/v1/simulate` unchanged.
StageListener: TypeAlias = Callable[[PipelineEvent], Awaitable[None]]
