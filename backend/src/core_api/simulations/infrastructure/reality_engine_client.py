"""HTTP implementation of the Reality Engine port.

Parses Reality Engine's responses with local Pydantic models (validated,
never raw dict indexing) and joins its three per-scenario collections
(scenarios, comparison matrix, ranking — see reality_engine's
`pipeline/orchestrator.py`) into the single `RealityEngineScenario` shape
this module's domain actually wants. This join is a wire-format concern,
so it lives here, not in the use case.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from pydantic import BaseModel

from core_api.simulations.domain.reality_engine_port import (
    RealityEngineCalibrationOutcome,
    RealityEngineCalibrationScenario,
    RealityEngineClient,
    RealityEngineError,
    RealityEngineRankedScenario,
    RealityEngineScenario,
    RealityEngineSimulationOutcome,
    RealityEngineStageEvent,
)


class _SafetyGateResponse(BaseModel):
    risk_level: str
    signals_detected: list[str]
    safe_to_proceed: bool
    recommended_action: str


class _AnalysisResponse(BaseModel):
    safety: _SafetyGateResponse


class _ScenarioResponse(BaseModel):
    id: str
    title: str
    narrative: str
    assumptions: list[str]
    relative_probability: float
    time_horizon_months: int


class _ScenariosResponse(BaseModel):
    scenarios: list[_ScenarioResponse]


class _ComparisonRowResponse(BaseModel):
    scenario_id: str
    goal_alignment_scores: list[dict[str, Any]]
    risk_score: float
    reversibility_score: float


class _ComparisonResponse(BaseModel):
    comparison_matrix: list[_ComparisonRowResponse]


class _RankedScenarioResponse(BaseModel):
    scenario_id: str
    final_score: float
    rank: int


class _RankingResponse(BaseModel):
    ranking: list[_RankedScenarioResponse]


class _SynthesisResponse(BaseModel):
    synthesis: str
    reflective_question: str


class _MemoryResponse(BaseModel):
    summary_text: str
    embedding: list[float]


class _SimulateResponse(BaseModel):
    analysis: _AnalysisResponse
    scenarios: _ScenariosResponse | None = None
    comparison: _ComparisonResponse | None = None
    ranking: _RankingResponse | None = None
    synthesis: _SynthesisResponse | None = None
    memory: _MemoryResponse | None = None


class _CalibrateResponse(BaseModel):
    closest_scenario_id: str | None
    calibration_delta: float
    system_errors_identified: list[str]
    user_bias_profile_update: dict[str, float]


class HttpRealityEngineClient(RealityEngineClient):
    #: Longer than the unary timeout: a streamed run reports progress
    #: throughout, so a slow pipeline is visibly alive rather than
    #: indistinguishable from a hang — the reason to wait longer at all.
    _stream_timeout = 120.0

    def __init__(self, base_url: str, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client or httpx.AsyncClient(timeout=45.0)

    async def simulate(
        self, raw_input: str, declared_goals: list[str]
    ) -> RealityEngineSimulationOutcome:
        try:
            response = await self._http_client.post(
                f"{self._base_url}/v1/simulate",
                json={"raw_input": raw_input, "declared_goals": declared_goals},
            )
            response.raise_for_status()
            parsed = _SimulateResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise RealityEngineError(f"Reality Engine request failed: {exc}") from exc

        return self._to_outcome(parsed)

    async def simulate_stream(
        self, raw_input: str, declared_goals: list[str]
    ) -> AsyncIterator[RealityEngineStageEvent | RealityEngineSimulationOutcome]:
        """Relays `/v1/simulate/stream`, one NDJSON line at a time.

        A line that doesn't parse, or an `error` line from the engine,
        raises rather than ending the iteration quietly: a consumer that
        just saw the stream stop has no way to tell a finished run from a
        broken one, and would persist neither.
        """
        parsed: _SimulateResponse | None = None
        try:
            async with self._http_client.stream(
                "POST",
                f"{self._base_url}/v1/simulate/stream",
                json={"raw_input": raw_input, "declared_goals": declared_goals},
                timeout=self._stream_timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    kind = event.get("type")
                    if kind == "stage":
                        yield RealityEngineStageEvent(
                            stage=str(event.get("stage", "")),
                            status=str(event.get("status", "")),
                        )
                    elif kind == "error":
                        raise RealityEngineError(
                            f"Reality Engine reported a failure: {event.get('message')}"
                        )
                    elif kind == "result":
                        parsed = _SimulateResponse.model_validate(event["result"])
                    # An unknown event type is skipped on purpose: the
                    # engine is free to add vocabulary without this relay
                    # having to be redeployed first.
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise RealityEngineError(f"Reality Engine stream failed: {exc}") from exc

        if parsed is None:
            raise RealityEngineError("Reality Engine stream ended without a result")
        yield self._to_outcome(parsed)

    def _to_outcome(self, parsed: _SimulateResponse) -> RealityEngineSimulationOutcome:
        safety = parsed.analysis.safety
        safety_gate_result = safety.model_dump()

        if not safety.safe_to_proceed or parsed.scenarios is None:
            return RealityEngineSimulationOutcome(
                safe_to_proceed=safety.safe_to_proceed,
                safety_gate_result=safety_gate_result,
            )

        if parsed.comparison is None or parsed.ranking is None or parsed.synthesis is None:
            raise RealityEngineError(
                "Reality Engine reported safe_to_proceed with scenarios but is "
                "missing comparison/ranking/synthesis"
            )

        comparison_by_id = {row.scenario_id: row for row in parsed.comparison.comparison_matrix}
        ranking_by_id = {row.scenario_id: row for row in parsed.ranking.ranking}

        try:
            scenarios = [
                RealityEngineScenario(
                    id=scenario.id,
                    title=scenario.title,
                    narrative=scenario.narrative,
                    assumptions=scenario.assumptions,
                    relative_probability=scenario.relative_probability,
                    time_horizon_months=scenario.time_horizon_months,
                    goal_alignment_scores=comparison_by_id[scenario.id].goal_alignment_scores,
                    risk_score=comparison_by_id[scenario.id].risk_score,
                    reversibility_score=comparison_by_id[scenario.id].reversibility_score,
                    final_score=ranking_by_id[scenario.id].final_score,
                    rank=ranking_by_id[scenario.id].rank,
                )
                for scenario in parsed.scenarios.scenarios
            ]
        except KeyError as exc:
            raise RealityEngineError(
                f"Reality Engine response is missing comparison/ranking data for scenario {exc}"
            ) from exc

        return RealityEngineSimulationOutcome(
            safe_to_proceed=True,
            safety_gate_result=safety_gate_result,
            scenarios=scenarios,
            synthesis_text=parsed.synthesis.synthesis,
            reflective_question=parsed.synthesis.reflective_question,
            memory_summary=parsed.memory.summary_text if parsed.memory else None,
            memory_embedding=tuple(parsed.memory.embedding) if parsed.memory else None,
        )

    async def calibrate(
        self,
        reported_outcome: str,
        original_scenarios: list[RealityEngineCalibrationScenario],
        original_ranking: list[RealityEngineRankedScenario],
    ) -> RealityEngineCalibrationOutcome:
        try:
            response = await self._http_client.post(
                f"{self._base_url}/v1/calibrate",
                json={
                    "reported_outcome": reported_outcome,
                    "original_scenarios": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "narrative": s.narrative,
                            "assumptions": s.assumptions,
                            "relative_probability": s.relative_probability,
                            "time_horizon_months": s.time_horizon_months,
                        }
                        for s in original_scenarios
                    ],
                    "original_ranking": [
                        {"scenario_id": r.scenario_id, "final_score": r.final_score, "rank": r.rank}
                        for r in original_ranking
                    ],
                },
            )
            response.raise_for_status()
            parsed = _CalibrateResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise RealityEngineError(f"Reality Engine calibrate request failed: {exc}") from exc

        return RealityEngineCalibrationOutcome(
            closest_scenario_id=parsed.closest_scenario_id,
            calibration_delta=parsed.calibration_delta,
            system_errors_identified=parsed.system_errors_identified,
            user_bias_profile_update=parsed.user_bias_profile_update,
        )
