"""enforce one reported outcome per decision

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-05

docs/DATABASE.md §2.9 always described `decision_outcomes` as at most one
row per decision, but 0006 only indexed `decision_id`. The application-
level guard in `ReportDecisionOutcomeUseCase` can still lose a race
between two concurrent reports, and a duplicate is not a harmless extra
row: each outcome folds another observation into the user's
`UserBiasProfile`, so a double report double-counts against their own
calibration.

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replaced rather than added alongside: a unique index serves every
    # lookup the plain one did, so keeping both would only cost writes.
    op.drop_index("ix_decision_outcomes_decision_id", table_name="decision_outcomes")
    op.create_index(
        "ix_decision_outcomes_decision_id",
        "decision_outcomes",
        ["decision_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_decision_outcomes_decision_id", table_name="decision_outcomes")
    op.create_index("ix_decision_outcomes_decision_id", "decision_outcomes", ["decision_id"])
