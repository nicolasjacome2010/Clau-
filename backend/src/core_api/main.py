"""FastAPI application factory for the Core API service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core_api.auth.token_verifier import SupabaseJWTVerifier
from core_api.config import Settings, get_settings
from core_api.crypto import FernetFieldEncryptor
from core_api.db import create_engine, create_session_factory
from core_api.decisions.api.router import router as decisions_router
from core_api.goals.api.router import router as goals_router
from core_api.identity.api.router import router as identity_router
from core_api.memory.api.router import router as memory_router
from core_api.simulations.api.router import router as simulations_router
from core_api.simulations.infrastructure.reality_engine_client import HttpRealityEngineClient


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url, echo=settings.environment == "development")
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)

        jwks_url = settings.supabase_jwks_url_override or (
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        )
        app.state.token_verifier = SupabaseJWTVerifier(
            jwks_url, audience=settings.supabase_jwt_audience
        )
        app.state.field_encryptor = FernetFieldEncryptor(settings.field_encryption_key)
        app.state.reality_engine_client = HttpRealityEngineClient(settings.reality_engine_base_url)

        yield

        await engine.dispose()

    app = FastAPI(title="VAR OS Core API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(identity_router)
    app.include_router(goals_router)
    app.include_router(decisions_router)
    app.include_router(simulations_router)
    app.include_router(memory_router)

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
