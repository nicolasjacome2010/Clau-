from __future__ import annotations

import pytest

from reality_engine.ai_gateway.application.gateway import AIGateway
from reality_engine.ai_gateway.domain.ports import ModelTier
from reality_engine.ai_gateway.infrastructure.fake_provider import FakeLLMProvider
from reality_engine.pipeline.agents.risk_analysis import RiskAnalysisAgent
from reality_engine.pipeline.domain.schemas import (
    ComprehensionOutput,
    OptionRisk,
    OptionRiskMap,
    RiskAnalysisOutput,
    RiskSeverity,
)


@pytest.mark.asyncio
async def test_returns_parsed_risk_map() -> None:
    expected = RiskAnalysisOutput(
        risk_map=[
            OptionRiskMap(
                option="Aceptar",
                risks=[
                    OptionRisk(
                        type="financiero",
                        severity=RiskSeverity.LOW,
                        reversibility=RiskSeverity.MEDIUM,
                    )
                ],
            )
        ]
    )
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = RiskAnalysisAgent(gateway)
    comprehension = ComprehensionOutput(
        decision_question="¿Debo aceptar?",
        explicit_options=["Aceptar", "Rechazar"],
        requires_clarification=False,
    )

    result = await agent.run(comprehension)

    assert result == expected


@pytest.mark.asyncio
async def test_trivial_option_can_have_no_risks() -> None:
    expected = RiskAnalysisOutput(risk_map=[OptionRiskMap(option="No hacer nada", risks=[])])
    provider = FakeLLMProvider(responses=[expected])
    gateway = AIGateway({ModelTier.STRUCTURED_EXTRACTION: [provider]})
    agent = RiskAnalysisAgent(gateway)
    comprehension = ComprehensionOutput(
        decision_question="¿Debo actuar?",
        explicit_options=["No hacer nada"],
        requires_clarification=False,
    )

    result = await agent.run(comprehension)

    assert result.risk_map[0].risks == []
