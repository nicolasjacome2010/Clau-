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


@lru_cache
def get_settings() -> Settings:
    return Settings()
