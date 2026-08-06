"""HTTP API for the Reality Engine service.

Agents 0-11 are implemented — see docs/REALITY_ENGINE.md for the full
13-agent pipeline. Agent 12 (Aprendizaje) is exposed here as its own
endpoint (`/v1/calibrate`), not part of `/v1/simulate` — see
`pipeline/agents/learning.py`'s docstring for why.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from reality_engine.ai_gateway.domain.ports import LLMGenerationError
from reality_engine.api.schemas import (
    AnalyzeRequest,
    CalibrateRequest,
    CalibrateResponse,
    SafetyCheckRequest,
    SafetyCheckResponse,
)
from reality_engine.api.streaming import stream_simulation
from reality_engine.pipeline.agents.learning import LearningAgent
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.domain.schemas import (
    RankedScenario,
    RankingOutput,
    Scenario,
    ScenariosOutput,
)
from reality_engine.pipeline.orchestrator import (
    AnalysisPipeline,
    AnalysisResult,
    SimulationPipeline,
    SimulationResult,
)

router = APIRouter(prefix="/v1", tags=["reality-engine"])


def get_safety_gate_agent(request: Request) -> SafetyGateAgent:
    return cast(SafetyGateAgent, request.app.state.safety_gate_agent)


def get_analysis_pipeline(request: Request) -> AnalysisPipeline:
    return cast(AnalysisPipeline, request.app.state.analysis_pipeline)


def get_simulation_pipeline(request: Request) -> SimulationPipeline:
    return cast(SimulationPipeline, request.app.state.simulation_pipeline)


def get_learning_agent(request: Request) -> LearningAgent:
    return cast(LearningAgent, request.app.state.learning_agent)


@router.post("/safety-check", response_model=SafetyCheckResponse)
async def safety_check(
    payload: SafetyCheckRequest,
    agent: Annotated[SafetyGateAgent, Depends(get_safety_gate_agent)],
) -> SafetyCheckResponse:
    result = await agent.run(payload.raw_input)
    return SafetyCheckResponse(
        risk_level=result.risk_level,
        signals_detected=result.signals_detected,
        safe_to_proceed=result.safe_to_proceed,
        recommended_action=result.recommended_action,
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(
    payload: AnalyzeRequest,
    pipeline: Annotated[AnalysisPipeline, Depends(get_analysis_pipeline)],
) -> AnalysisResult:
    return await pipeline.run(payload.raw_input, declared_goals=payload.declared_goals)


@router.post("/simulate", response_model=SimulationResult)
async def simulate(
    payload: AnalyzeRequest,
    pipeline: Annotated[SimulationPipeline, Depends(get_simulation_pipeline)],
) -> SimulationResult:
    return await pipeline.run(payload.raw_input, declared_goals=payload.declared_goals)


@router.post("/simulate/stream")
async def simulate_stream(
    payload: AnalyzeRequest,
    pipeline: Annotated[SimulationPipeline, Depends(get_simulation_pipeline)],
) -> StreamingResponse:
    """The same run as `/v1/simulate`, reporting each stage as it happens.

    A separate endpoint rather than a flag on the existing one: the two
    have different response *shapes* (one document vs. a sequence of
    lines), and a single path that returns either depending on a parameter
    is a path whose contract can't be written down.
    """
    return StreamingResponse(
        stream_simulation(pipeline, payload.raw_input, payload.declared_goals),
        media_type="application/x-ndjson",
    )


@router.post("/calibrate", response_model=CalibrateResponse)
async def calibrate(
    payload: CalibrateRequest,
    agent: Annotated[LearningAgent, Depends(get_learning_agent)],
) -> CalibrateResponse:
    original_scenarios = ScenariosOutput(
        scenarios=[Scenario(**s.model_dump()) for s in payload.original_scenarios]
    )
    original_ranking = RankingOutput(
        ranking=[RankedScenario(**r.model_dump()) for r in payload.original_ranking]
    )
    try:
        result = await agent.run(payload.reported_outcome, original_scenarios, original_ranking)
    except LLMGenerationError as exc:
        # Unlike Agent 0, there is no safe default to fall back to here —
        # calibration is opt-in analysis, not a safety gate, so a
        # misconfigured/unavailable provider is a real 503, not silently
        # swallowed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Calibration is temporarily unavailable",
        ) from exc
    return CalibrateResponse(
        closest_scenario_id=result.closest_scenario_id,
        calibration_delta=result.calibration_delta,
        system_errors_identified=result.system_errors_identified,
        user_bias_profile_update=result.user_bias_profile_update,
    )
