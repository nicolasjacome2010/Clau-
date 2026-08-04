"""create decision_outcomes table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-04

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_outcome", sa.String(), nullable=False),
        sa.Column("closest_scenario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("calibration_delta", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "system_errors_identified",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["closest_scenario_id"], ["simulation_scenarios.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_decision_outcomes_decision_id", "decision_outcomes", ["decision_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_outcomes_decision_id", table_name="decision_outcomes")
    op.drop_table("decision_outcomes")
