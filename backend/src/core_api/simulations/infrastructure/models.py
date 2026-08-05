"""SQLAlchemy ORM models for the simulations bounded context.

Maps to `simulations` (docs/DATABASE.md §2.5) and `simulation_scenarios`
(§2.7). `simulation_synthesis` (§2.8) is folded into `simulations` as two
nullable columns instead of a separate 1:1 table — it's always read/written
together with the parent row and splitting it out would only add a join,
not a real invariant boundary (unlike `simulation_scenarios`, which is a
true 1:N collection).

`simulation_steps` (§2.6, per-agent audit trail) is not implemented yet:
Reality Engine's `/v1/simulate` doesn't report per-agent latency/cost
telemetry today (see reality_engine/README.md), so there's nothing to
store there yet.

`DecisionOutcomeModel` maps `decision_outcomes` (§2.9) — the "cierre de
ciclo" record fed by Reality Engine's Agent 12 (Aprendizaje).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_api.db import Base, UTCDateTime

_JSONType = JSON().with_variant(JSONB, "postgresql")


class SimulationModel(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String, index=True)
    pipeline_version: Mapped[str] = mapped_column(String)
    safety_gate_result: Mapped[dict[str, Any]] = mapped_column(_JSONType, default=dict)
    synthesis_text: Mapped[str | None] = mapped_column(String, nullable=True)
    reflective_question: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class SimulationScenarioModel(Base):
    __tablename__ = "simulation_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulations.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    narrative: Mapped[str] = mapped_column(String)
    assumptions: Mapped[list[str]] = mapped_column(_JSONType, default=list)
    relative_probability: Mapped[float] = mapped_column(Numeric(5, 2))
    time_horizon_months: Mapped[int] = mapped_column(SmallInteger)
    goal_alignment_scores: Mapped[list[dict[str, Any]]] = mapped_column(_JSONType, default=list)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2))
    reversibility_score: Mapped[float] = mapped_column(Numeric(5, 2))
    final_score: Mapped[float] = mapped_column(Numeric(5, 2))
    rank: Mapped[int] = mapped_column(SmallInteger)


class DecisionOutcomeModel(Base):
    __tablename__ = "decision_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    # Unique, not merely indexed: "at most one outcome per decision"
    # (docs/DATABASE.md §2.9) is an invariant, and the use case's guard
    # can still lose a race between two concurrent reports. The database
    # is the only place that can't be bypassed.
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), index=True, unique=True
    )
    reported_outcome: Mapped[str] = mapped_column(String)
    closest_scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("simulation_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    calibration_delta: Mapped[float] = mapped_column(Numeric(6, 2))
    system_errors_identified: Mapped[list[str]] = mapped_column(_JSONType, default=list)
    reported_at: Mapped[datetime] = mapped_column(UTCDateTime)
