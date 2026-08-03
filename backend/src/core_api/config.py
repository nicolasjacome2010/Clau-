"""Application settings, loaded from environment variables (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="VAROS_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://varos:varos@localhost:5432/varos"

    supabase_url: str = "https://your-project.supabase.co"
    supabase_jwt_audience: str = "authenticated"
    # In production the JWKS is fetched from `{supabase_url}/auth/v1/.well-known/jwks.json`
    # and cached (see core_api/auth/token_verifier.py). This override exists for local/dev
    # environments that run against a self-hosted Supabase or a static test key.
    supabase_jwks_url_override: str | None = None

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    # DEV-ONLY DEFAULT. Production must override this via VAROS_FIELD_ENCRYPTION_KEY
    # with a key derived from AWS KMS per docs/ARCHITECTURE.md §11 — never reuse
    # this value outside local development.
    field_encryption_key: str = "8QaRBSQOvwlezcaKrQvir-q8zngdayjGpHYtlM3tHxc="


@lru_cache
def get_settings() -> Settings:
    return Settings()
