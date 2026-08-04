"""FastAPI application factory for the Reality Engine service.

Standalone service, separate from Core API (docs/ARCHITECTURE.md §2.2):
its load profile — IO-bound waiting on LLM calls, high latency, needs
queuing — is fundamentally different from the rest of the CRUD backend.
"""

from __future__ import annotations

from fastapi import FastAPI

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import EmbeddingProvider, LLMProvider, ModelTier
from reality_engine.api.router import router as reality_engine_router
from reality_engine.config import Settings, get_settings
from reality_engine.pipeline.agents.learning import LearningAgent
from reality_engine.pipeline.agents.safety_gate import SafetyGateAgent
from reality_engine.pipeline.orchestrator import AnalysisPipeline, SimulationPipeline


def _build_providers_by_tier(settings: Settings) -> dict[ModelTier, list[LLMProvider]]:
    providers: dict[ModelTier, list[LLMProvider]] = {tier: [] for tier in ModelTier}

    if settings.openai_api_key:
        # Imported lazily so the `openai` package (and its own optional
        # dependencies) is only required when a key is actually configured.
        from openai import AsyncOpenAI

        from reality_engine.ai_gateway.infrastructure.openai_provider import OpenAIProvider

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        providers[ModelTier.SAFETY_CLASSIFICATION] = [
            OpenAIProvider(client, model=settings.openai_safety_model)
        ]
        providers[ModelTier.STRUCTURED_EXTRACTION] = [
            OpenAIProvider(client, model=settings.openai_extraction_model)
        ]
        providers[ModelTier.REASONING_CREATIVE] = [
            OpenAIProvider(client, model=settings.openai_reasoning_model)
        ]

    return providers


def _build_embedding_providers(settings: Settings) -> list[EmbeddingProvider]:
    if not settings.openai_api_key:
        return []

    from openai import AsyncOpenAI

    from reality_engine.ai_gateway.infrastructure.openai_embedding_provider import (
        OpenAIEmbeddingProvider,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    return [OpenAIEmbeddingProvider(client, model=settings.openai_embedding_model)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="VAR OS Reality Engine", version="0.1.0")

    gateway = AIGateway(
        _build_providers_by_tier(settings),
        embedding_providers=_build_embedding_providers(settings),
    )
    app.state.safety_gate_agent = SafetyGateAgent(gateway)
    app.state.analysis_pipeline = AnalysisPipeline(gateway)
    app.state.simulation_pipeline = SimulationPipeline(gateway)
    app.state.learning_agent = LearningAgent(gateway)

    app.include_router(reality_engine_router)

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
