from __future__ import annotations

import json

from fastapi.testclient import TestClient

from reality_engine.main import create_app


def test_safety_check_without_configured_provider_fails_safe() -> None:
    """No OPENAI_API_KEY set anywhere in this test process, so the safety
    tier has zero providers and the endpoint must fail safe (see
    config.py and pipeline/agents/safety_gate.py).
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/safety-check", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_action"] == "halt_and_refer"


def test_safety_check_deterministic_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/safety-check", json={"raw_input": "quiero quitarme la vida"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "acute_risk"
    assert body["safe_to_proceed"] is False


def test_safety_check_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/safety-check", json={"raw_input": ""})

    assert response.status_code == 422


def test_analyze_without_configured_provider_fails_safe_and_skips_extraction() -> None:
    """Same posture as /v1/safety-check: without OPENAI_API_KEY, Agent 0
    fails safe and the pipeline never reaches Agents 1-6.
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/analyze", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["safety"]["recommended_action"] == "halt_and_refer"
    assert body["comprehension"] is None
    assert body["summary"] is None


def test_analyze_deterministic_risk_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/analyze", json={"raw_input": "quiero quitarme la vida"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["safety"]["risk_level"] == "acute_risk"
    assert body["comprehension"] is None


def test_analyze_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/analyze", json={"raw_input": ""})

    assert response.status_code == 422


def test_analyze_rejects_too_many_declared_goals() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/analyze",
            json={"raw_input": "algo", "declared_goals": ["a", "b", "c", "d", "e", "f"]},
        )

    assert response.status_code == 422


def test_simulate_without_configured_provider_fails_safe() -> None:
    """/v1/simulate shares Agent 0 with /v1/safety-check and /v1/analyze —
    without OPENAI_API_KEY it must fail safe and never reach Agents 1-10.
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["safety"]["recommended_action"] == "halt_and_refer"
    assert body["scenarios"] is None
    assert body["synthesis"] is None


def test_simulate_deterministic_risk_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": "quiero quitarme la vida"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["safety"]["risk_level"] == "acute_risk"
    assert body["scenarios"] is None


def test_simulate_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": ""})

    assert response.status_code == 422


def _three_scenarios() -> list[dict[str, object]]:
    return [
        {
            "id": f"s{i}",
            "title": f"Escenario {i}",
            "narrative": "Podrías crecer profesionalmente.",
            "relative_probability": 33.3,
            "time_horizon_months": 12,
        }
        for i in range(3)
    ]


def test_calibrate_without_configured_provider_returns_503() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "Acepté y me tomó 3 meses adaptarme",
                "original_scenarios": _three_scenarios(),
                "original_ranking": [],
            },
        )

    assert response.status_code == 503


def test_calibrate_rejects_too_few_scenarios() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "algo",
                "original_scenarios": _three_scenarios()[:2],
                "original_ranking": [],
            },
        )

    assert response.status_code == 422


def test_calibrate_rejects_empty_outcome() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "",
                "original_scenarios": _three_scenarios(),
                "original_ranking": [],
            },
        )

    assert response.status_code == 422


def test_healthz_is_public() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _lines(body: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def test_simulate_stream_reports_stages_and_ends_with_a_result() -> None:
    """Without OPENAI_API_KEY the run halts at Agent 0 — which is exactly
    the shape a client must be able to read off the stream: the gate's two
    edges, an explicit halt, then the result.
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate/stream", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")

    events = _lines(response.text)
    assert events[0] == {"type": "stage", "stage": "safety_gate", "status": "started"}
    assert events[1] == {"type": "stage", "stage": "safety_gate", "status": "completed"}
    assert events[2] == {"type": "halted"}
    # The result still comes down the same stream: a halted run is a
    # finished run, and the client renders a referral from it.
    assert events[-1]["type"] == "result"
    result = events[-1]["result"]
    assert isinstance(result, dict)
    assert result["scenarios"] is None


def test_simulate_stream_is_valid_ndjson_line_by_line() -> None:
    # One JSON document per line and nothing else — the contract a
    # line-buffered client depends on.
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/simulate/stream", json={"raw_input": "quiero quitarme la vida"}
        )

    for line in response.text.splitlines():
        assert json.loads(line)["type"] in {"stage", "halted", "result", "error"}


def test_simulate_stream_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate/stream", json={"raw_input": ""})

    assert response.status_code == 422
