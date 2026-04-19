"""Add destination_id (nullable UUID) to trips for data-service linkage.

No FK constraint: logical link only, per cross-service architecture rules.

Revision ID: c1a2b3d4e5f6
Revises: ba39d2e860e8
Create Date: 2026-04-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ba39d2e860e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("destination_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_trips_destination_id", "trips", ["destination_id"])


def downgrade() -> None:
    op.drop_index("ix_trips_destination_id", table_name="trips")
    op.drop_column("trips", "destination_id")
