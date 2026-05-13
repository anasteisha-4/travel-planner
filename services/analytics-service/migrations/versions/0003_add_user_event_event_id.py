"""Add event_id to user_events

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_events", sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_user_events_event_id", "user_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_events_event_id", table_name="user_events")
    op.drop_column("user_events", "event_id")
