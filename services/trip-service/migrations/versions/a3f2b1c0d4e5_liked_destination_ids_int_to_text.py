"""liked_destination_ids int to text

Revision ID: a3f2b1c0d4e5
Revises: e91dd317f15e
Create Date: 2026-04-20 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3f2b1c0d4e5"
down_revision = "e91dd317f15e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_user_profiles_liked_destination_ids", table_name="user_profiles", postgresql_using="gin")
    op.alter_column(
        "user_profiles",
        "liked_destination_ids",
        type_=postgresql.ARRAY(sa.Text()),
        postgresql_using="liked_destination_ids::text[]",
        existing_nullable=True,
    )
    op.create_index(
        "ix_user_profiles_liked_destination_ids",
        "user_profiles",
        ["liked_destination_ids"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_user_profiles_liked_destination_ids", table_name="user_profiles", postgresql_using="gin")
    op.alter_column(
        "user_profiles",
        "liked_destination_ids",
        type_=postgresql.ARRAY(sa.Integer()),
        postgresql_using="liked_destination_ids::integer[]",
        existing_nullable=True,
    )
    op.create_index(
        "ix_user_profiles_liked_destination_ids",
        "user_profiles",
        ["liked_destination_ids"],
        unique=False,
        postgresql_using="gin",
    )
