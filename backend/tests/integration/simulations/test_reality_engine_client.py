"""Tests the HTTP Reality Engine client against a mocked transport — no
real network call, exercises the real httpx request/response path.
"""

from __future__ import annotations

import json

import httpx
import pytest

from core_api.simulations.domain.reality_engine_port import RealityEngineError
from core_api.simulations.infrastructure.reality_engine_client import HttpRealityEngineClient

_SAFE_BODY = {
    "analysis": {
        "safety": {
            "risk_level": "none",
            "signals_detected": [],
            "safe_to_proceed": True,
            "recommended_action": "proceed",
        }
    },
    "scenarios": {
        "scenarios": [
            {
                "id": "a",
                "title": "Aceptas",
                "narrative": "Podrías crecer.",
                "assumptions": [],
                "relative_probability": 60.0,
                "time_horizon_months": 12,
            }
        ]
    },
    "comparison": {
        "comparison_matrix": [
            {
                "scenario_id": "a",
                "goal_alignment_scores": [
                    {"goal": "Estabilidad", "score": 80, "justification": "x"}
                ],
                "risk_score": 30.0,
                "reversibility_score": 50.0,
            }
        ]
    },
    "ranking": {"ranking": [{"scenario_id": "a", "final_score": 70.0, "rank": 1}]},
    "synthesis": {"synthesis": "texto", "reflective_question": "¿Y bien?"},
}

_UNSAFE_BODY = {
    "analysis": {
        "safety": {
            "risk_level": "acute_risk",
            "signals_detected": ["pattern"],
            "safe_to_proceed": False,
            "recommended_action": "halt_and_refer",
        }
    },
    "scenarios": None,
    "comparison": None,
    "ranking": None,
    "synthesis": None,
}


def _client_with_response(status_code: int, body: object) -> HttpRealityEngineClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/simulate"
        payload = json.loads(request.content)
        assert "raw_input" in payload
        assert "declared_goals" in payload
        return httpx.Response(status_code, json=body)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HttpRealityEngineClient("http://reality-engine.internal", http_client=http_client)


@pytest.mark.asyncio
async def test_simulate_joins_scenarios_comparison_and_ranking_by_id() -> None:
    client = _client_with_response(200, _SAFE_BODY)

    outcome = await client.simulate("¿Debo aceptar?", ["Estabilidad"])

    assert outcome.safe_to_proceed is True
    assert len(outcome.scenarios) == 1
    scenario = outcome.scenarios[0]
    assert scenario.title == "Aceptas"
    assert scenario.risk_score == 30.0
    assert scenario.reversibility_score == 50.0
    assert scenario.final_score == 70.0
    assert scenario.rank == 1
    assert scenario.goal_alignment_scores[0]["goal"] == "Estabilidad"
    assert outcome.synthesis_text == "texto"
    assert outcome.reflective_question == "¿Y bien?"


@pytest.mark.asyncio
async def test_simulate_returns_unsafe_outcome_without_scenarios() -> None:
    client = _client_with_response(200, _UNSAFE_BODY)

    outcome = await client.simulate("contenido de riesgo", [])

    assert outcome.safe_to_proceed is False
    assert outcome.scenarios == []
    assert outcome.safety_gate_result["risk_level"] == "acute_risk"


@pytest.mark.asyncio
async def test_simulate_raises_on_non_2xx_response() -> None:
    client = _client_with_response(500, {"detail": "internal error"})

    with pytest.raises(RealityEngineError):
        await client.simulate("algo", [])


@pytest.mark.asyncio
async def test_simulate_raises_on_malformed_response_shape() -> None:
    client = _client_with_response(200, {"unexpected": "shape"})

    with pytest.raises(RealityEngineError):
        await client.simulate("algo", [])


@pytest.mark.asyncio
async def test_simulate_raises_when_scenario_missing_from_comparison() -> None:
    body = {
        "analysis": {
            "safety": {
                "risk_level": "none",
                "signals_detected": [],
                "safe_to_proceed": True,
                "recommended_action": "proceed",
            }
        },
        "scenarios": {
            "scenarios": [
                {
                    "id": "a",
                    "title": "t",
                    "narrative": "n",
                    "assumptions": [],
                    "relative_probability": 100.0,
                    "time_horizon_months": 12,
                }
            ]
        },
        "comparison": {"comparison_matrix": []},  # missing scenario "a"
        "ranking": {"ranking": [{"scenario_id": "a", "final_score": 70.0, "rank": 1}]},
        "synthesis": {"synthesis": "texto", "reflective_question": "¿Y bien?"},
    }
    client = _client_with_response(200, body)

    with pytest.raises(RealityEngineError):
        await client.simulate("algo", [])
