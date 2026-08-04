"""Reality Engine service settings, loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VAROS_RE_", extra="ignore")

    environment: str = "development"

    # If unset, no OpenAI provider is wired up and the safety-classification
    # tier has zero providers — SafetyGateAgent then always fails safe to
    # HALT_AND_REFER (see pipeline/agents/safety_gate.py). This is
    # intentional: a misconfigured deployment must never silently let
    # unscreened input through.
    openai_api_key: str | None = None
    openai_safety_model: str = "gpt-5-mini"
    # docs/ARCHITECTURE.md §2.6, tier "structured-extraction": Agents 1-6
    # and 8 (Comprensión through Análisis de Riesgos, plus Comparación) use
    # a cheaper/faster model than the creative-reasoning tier below.
    openai_extraction_model: str = "gpt-5-mini"
    # docs/ARCHITECTURE.md §2.6, tier "reasoning-creative": Agents 7
    # (Generación de Escenarios) and 10 (Síntesis) — the two agents whose
    # output quality matters most, so they get the stronger model.
    openai_reasoning_model: str = "gpt-5.1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
