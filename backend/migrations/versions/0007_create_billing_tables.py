"""create billing tables (subscriptions, stripe_events)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-04

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_unique_constraint(
        "uq_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"]
    )
    op.create_unique_constraint(
        "uq_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"]
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"]
    )

    op.create_table(
        "stripe_events",
        sa.Column("stripe_event_id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stripe_events_type", "stripe_events", ["type"])
    op.create_index("ix_stripe_events_processed_at", "stripe_events", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_stripe_events_processed_at", table_name="stripe_events")
    op.drop_index("ix_stripe_events_type", table_name="stripe_events")
    op.drop_table("stripe_events")
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_table("subscriptions")
