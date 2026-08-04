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


def test_healthz_is_public() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
