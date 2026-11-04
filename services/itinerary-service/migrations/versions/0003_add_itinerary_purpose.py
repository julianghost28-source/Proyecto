"""Add optional purpose to itinerary records."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_itinerary_purpose"
down_revision = "0002_transactional_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "itineraries",
        sa.Column("purpose", sa.String(length=250), nullable=False, server_default=""),
    )
    op.alter_column("itineraries", "purpose", server_default=None)


def downgrade() -> None:
    op.drop_column("itineraries", "purpose")
