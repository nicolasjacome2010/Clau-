"""Application use cases for the privacy bounded context.

Both use cases are cross-context by nature — a person's data does not
respect our module boundaries — so they take every repository they read
through as a constructor argument, the same way `RunSimulationUseCase`
does. The coupling is visible at the constructor rather than hidden
inside a repository that reaches across schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core_api.billing.domain.entities import SubscriptionStatus, SubscriptionTier
from core_api.billing.domain.repositories import SubscriptionRepository
from core_api.decisions.domain.entities import Decision
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.goals.domain.entities import Goal
from core_api.goals.domain.repositories import GoalRepository
from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.domain.repositories import UserProfileRepository, UserRepository
from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository
from core_api.privacy.domain.entities import UserDataExport
from core_api.privacy.domain.exceptions import ActiveSubscriptionError, UserNotFoundError
from core_api.simulations.domain.entities import DecisionOutcome, Simulation
from core_api.simulations.domain.repositories import DecisionOutcomeRepository, SimulationRepository

# Statuses that mean money is still moving. `canceled` is absent on
# purpose: a canceled subscription bills nothing further, so it is no
# reason to refuse an erasure.
_BILLING_ACTIVE_STATUSES = frozenset(
    {SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE, SubscriptionStatus.TRIALING}
)


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "locale": user.locale,
        "onboarding_completed_at": user.onboarding_completed_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _serialize_profile(profile: UserProfile) -> dict[str, Any]:
    return {
        "life_context": profile.life_context,
        "risk_tolerance": profile.risk_tolerance,
        "timezone": profile.timezone,
    }


def _serialize_goal(goal: Goal) -> dict[str, Any]:
    return {
        "id": str(goal.id),
        "name": goal.name,
        "default_weight": goal.default_weight,
        "is_active": goal.is_active,
        "created_at": goal.created_at,
    }


def _serialize_decision(decision: Decision) -> dict[str, Any]:
    return {
        "id": str(decision.id),
        "title": decision.title,
        "vertical": decision.vertical.value,
        "status": decision.status.value,
        # Decrypted here because the repository decrypts on read: an export
        # of ciphertext the user has no key for would satisfy the letter of
        # the right and none of its point.
        "raw_input": decision.raw_input,
        "created_at": decision.created_at,
        "updated_at": decision.updated_at,
    }


def _serialize_simulation(simulation: Simulation) -> dict[str, Any]:
    return {
        "id": str(simulation.id),
        "decision_id": str(simulation.decision_id),
        "status": simulation.status.value,
        "pipeline_version": simulation.pipeline_version,
        "safety_gate_result": simulation.safety_gate_result,
        "scenarios": [
            {
                "id": str(scenario.id),
                "title": scenario.title,
                "narrative": scenario.narrative,
                "assumptions": list(scenario.assumptions),
                "relative_probability": scenario.relative_probability,
                "time_horizon_months": scenario.time_horizon_months,
                "goal_alignment_scores": scenario.goal_alignment_scores,
                "risk_score": scenario.risk_score,
                "reversibility_score": scenario.reversibility_score,
                "final_score": scenario.final_score,
                "rank": scenario.rank,
            }
            for scenario in simulation.scenarios
        ],
        "synthesis_text": simulation.synthesis_text,
        "reflective_question": simulation.reflective_question,
        "started_at": simulation.started_at,
        "completed_at": simulation.completed_at,
    }


def _serialize_outcome(outcome: DecisionOutcome) -> dict[str, Any]:
    return {
        "id": str(outcome.id),
        "decision_id": str(outcome.decision_id),
        "reported_outcome": outcome.reported_outcome,
        "closest_scenario_id": (
            str(outcome.closest_scenario_id) if outcome.closest_scenario_id else None
        ),
        "calibration_delta": outcome.calibration_delta,
        "system_errors_identified": list(outcome.system_errors_identified),
        "reported_at": outcome.reported_at,
    }


def _serialize_bias_profile(profile: UserBiasProfile) -> dict[str, Any]:
    return {
        "calibration_score": profile.calibration_score,
        "updated_at": profile.updated_at,
        "biases": [
            {
                "bias": observation.bias,
                "score": observation.score,
                "occurrences": observation.occurrences,
            }
            for observation in profile.biases
        ],
    }


def _serialize_memory(memory: MemoryEmbedding) -> dict[str, Any]:
    return {
        "id": str(memory.id),
        "decision_id": str(memory.decision_id) if memory.decision_id else None,
        "summary_text": memory.summary_text,
        # The vector itself is left out on purpose — see
        # `UserDataExport.notes`. It encodes this same text and nothing
        # more, and 1536 floats would only make the export unreadable.
        "created_at": memory.created_at,
    }


@dataclass(frozen=True, slots=True)
class PrivacyRepositories:
    """Every repository the two use cases read through.

    Grouped into one object because the alternative is a nine-argument
    constructor twice over; it stays a plain dataclass of interfaces, so
    the Dependency Inversion is unchanged.
    """

    users: UserRepository
    profiles: UserProfileRepository
    goals: GoalRepository
    decisions: DecisionRepository
    simulations: SimulationRepository
    outcomes: DecisionOutcomeRepository
    bias_profiles: UserBiasProfileRepository
    memories: MemoryEmbeddingRepository
    subscriptions: SubscriptionRepository


class ExportUserDataUseCase:
    def __init__(self, repositories: PrivacyRepositories) -> None:
        self._repos = repositories

    async def execute(self, user_id: UUID) -> UserDataExport:
        user = await self._repos.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        profile = await self._repos.profiles.get_by_user_id(user_id)
        # `active_only=False`: an export is not a product view. A goal the
        # user retired is still something we hold about them.
        goals = await self._repos.goals.list_for_user(user_id, active_only=False)
        decisions = await self._repos.decisions.list_for_user(user_id)

        simulations: list[Simulation] = []
        for decision in decisions:
            simulations.extend(await self._repos.simulations.list_for_decision(decision.id))
        outcomes = await self._repos.outcomes.list_for_decisions([d.id for d in decisions])

        bias_profile = await self._repos.bias_profiles.get_by_user_id(user_id)
        memories = await self._repos.memories.list_for_user(user_id)
        subscription = await self._repos.subscriptions.get_by_user_id(user_id)

        return UserDataExport(
            exported_at=datetime.now(UTC),
            user=_serialize_user(user),
            profile=_serialize_profile(profile) if profile else None,
            goals=[_serialize_goal(goal) for goal in goals],
            decisions=[_serialize_decision(decision) for decision in decisions],
            simulations=[_serialize_simulation(simulation) for simulation in simulations],
            decision_outcomes=[_serialize_outcome(outcome) for outcome in outcomes],
            bias_profile=_serialize_bias_profile(bias_profile) if bias_profile else None,
            memories=[_serialize_memory(memory) for memory in memories],
            subscription=(
                {
                    "tier": subscription.tier.value,
                    "status": subscription.status.value,
                    "current_period_end": subscription.current_period_end,
                }
                if subscription
                else None
            ),
        )


class EraseUserDataUseCase:
    """Deletes the user and everything the schema hangs off them.

    One `UserRepository.delete`, not a cascade re-implemented in Python:
    docs/DATABASE.md already declares every user-owned table as
    `ON DELETE CASCADE` from `users.id`, and a second copy of that tree in
    application code is a copy that drifts the day a table is added.
    """

    def __init__(self, repositories: PrivacyRepositories) -> None:
        self._repos = repositories

    async def execute(self, user_id: UUID) -> None:
        user = await self._repos.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        subscription = await self._repos.subscriptions.get_by_user_id(user_id)
        if (
            subscription is not None
            and subscription.tier is not SubscriptionTier.FREE
            and subscription.status in _BILLING_ACTIVE_STATUSES
        ):
            raise ActiveSubscriptionError(user_id)

        await self._repos.users.delete(user_id)
