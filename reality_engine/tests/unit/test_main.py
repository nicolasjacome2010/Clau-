"""Tests `_build_providers_by_tier`'s wiring — no network calls, since
constructing an `AsyncOpenAI`/`AsyncAnthropic` client doesn't call out;
what's under test is *which* providers land in *which* tier's list, and in
what order (order is what the gateway's fallback loop tries first).
"""

from __future__ import annotations

from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.anthropic_provider import AnthropicProvider
from reality_engine.ai_gateway.infrastructure.openai_provider import OpenAIProvider
from reality_engine.config import Settings
from reality_engine.main import _build_providers_by_tier


def test_no_keys_configured_leaves_every_tier_empty() -> None:
    settings = Settings(openai_api_key=None, anthropic_api_key=None)

    providers = _build_providers_by_tier(settings)

    assert providers[ModelTier.REASONING_CREATIVE] == []
    assert providers[ModelTier.STRUCTURED_EXTRACTION] == []
    assert providers[ModelTier.SAFETY_CLASSIFICATION] == []


def test_openai_only_serves_all_three_tiers_alone() -> None:
    settings = Settings(openai_api_key="sk-test", anthropic_api_key=None)

    providers = _build_providers_by_tier(settings)

    assert [type(p) for p in providers[ModelTier.REASONING_CREATIVE]] == [OpenAIProvider]
    assert [type(p) for p in providers[ModelTier.STRUCTURED_EXTRACTION]] == [OpenAIProvider]
    assert [type(p) for p in providers[ModelTier.SAFETY_CLASSIFICATION]] == [OpenAIProvider]


def test_anthropic_only_serves_reasoning_creative_alone() -> None:
    # docs/ARCHITECTURE.md §2.6: Claude is documented for reasoning-creative
    # only — it must never appear in safety-classification or
    # structured-extraction, configured or not.
    settings = Settings(openai_api_key=None, anthropic_api_key="sk-ant-test")

    providers = _build_providers_by_tier(settings)

    assert [type(p) for p in providers[ModelTier.REASONING_CREATIVE]] == [AnthropicProvider]
    assert providers[ModelTier.STRUCTURED_EXTRACTION] == []
    assert providers[ModelTier.SAFETY_CLASSIFICATION] == []


def test_both_keys_configured_openai_is_primary_anthropic_is_fallback() -> None:
    # "OpenAI (primario), Claude (fallback si OpenAI degrada)" — order in
    # the list is what AIGateway's retry/fallback loop tries first.
    settings = Settings(openai_api_key="sk-test", anthropic_api_key="sk-ant-test")

    providers = _build_providers_by_tier(settings)

    assert [type(p) for p in providers[ModelTier.REASONING_CREATIVE]] == [
        OpenAIProvider,
        AnthropicProvider,
    ]
    # Untouched by the Anthropic branch — still OpenAI-only.
    assert [type(p) for p in providers[ModelTier.STRUCTURED_EXTRACTION]] == [OpenAIProvider]
    assert [type(p) for p in providers[ModelTier.SAFETY_CLASSIFICATION]] == [OpenAIProvider]
