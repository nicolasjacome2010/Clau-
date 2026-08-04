"""HTTP API for the Reality Engine service.

Only Agent 0 (Risk & Safety Gate) is implemented so far — see
docs/REALITY_ENGINE.md for the full 13-agent pipeline this will grow into.
There is no `/v1/simulate` endpoint yet; that requires Agents 1-12, which
are not built.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from reality_engine.api.schemas import SafetyCheckRequest, SafetyCheckResponse
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent

router = APIRouter(prefix="/v1", tags=["reality-engine"])


def get_safety_gate_agent(request: Request) -> SafetyGateAgent:
    return cast(SafetyGateAgent, request.app.state.safety_gate_agent)


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
