from __future__ import annotations

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


def test_healthz_is_public() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
