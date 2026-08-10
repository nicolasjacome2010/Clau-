"""create simulations tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-04

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("pipeline_version", sa.String(), nullable=False),
        sa.Column(
            "safety_gate_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("synthesis_text", sa.String(), nullable=True),
        sa.Column("reflective_question", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_simulations_decision_id", "simulations", ["decision_id"])
    op.create_index("ix_simulations_status", "simulations", ["status"])

    op.create_table(
        "simulation_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("narrative", sa.String(), nullable=False),
        sa.Column(
            "assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column("relative_probability", sa.Numeric(5, 2), nullable=False),
        sa.Column("time_horizon_months", sa.SmallInteger(), nullable=False),
        sa.Column(
            "goal_alignment_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("reversibility_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("final_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_simulation_scenarios_simulation_id", "simulation_scenarios", ["simulation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_simulation_scenarios_simulation_id", table_name="simulation_scenarios")
    op.drop_table("simulation_scenarios")
    op.drop_index("ix_simulations_status", table_name="simulations")
    op.drop_index("ix_simulations_decision_id", table_name="simulations")
    op.drop_table("simulations")
