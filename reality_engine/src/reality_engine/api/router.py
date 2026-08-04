"""HTTP API for the Reality Engine service.

Agents 0-6 are implemented — see docs/REALITY_ENGINE.md for the full
13-agent pipeline this will grow into. There is no `/v1/simulate` endpoint
yet; that requires Agents 7-12 (scenario generation onward), which are not
built.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from reality_engine.api.schemas import AnalyzeRequest, SafetyCheckRequest, SafetyCheckResponse
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.orchestrator import AnalysisPipeline, AnalysisResult

router = APIRouter(prefix="/v1", tags=["reality-engine"])


def get_safety_gate_agent(request: Request) -> SafetyGateAgent:
    return cast(SafetyGateAgent, request.app.state.safety_gate_agent)


def get_analysis_pipeline(request: Request) -> AnalysisPipeline:
    return cast(AnalysisPipeline, request.app.state.analysis_pipeline)


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
