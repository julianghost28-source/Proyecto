"""Create itinerary records.

Revision ID: 0001_create_itineraries
Revises:
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_create_itineraries"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itineraries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_name", sa.String(length=120), nullable=False),
        sa.Column("origin_airport_id", sa.Integer(), nullable=False),
        sa.Column("destination_airport_id", sa.Integer(), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("origin_airport_id <> destination_airport_id", name="ck_itineraries_different_airports"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_itineraries_positive_duration"),
    )
    op.create_index("ix_itineraries_travel_date", "itineraries", ["travel_date"])


def downgrade() -> None:
    op.drop_index("ix_itineraries_travel_date", table_name="itineraries")
    op.drop_table("itineraries")
