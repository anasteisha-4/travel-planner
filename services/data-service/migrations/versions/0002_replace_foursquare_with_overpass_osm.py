"""Replace foursquare with overpass_osm in poisource enum

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-28

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE poisource RENAME VALUE 'foursquare' TO 'overpass_osm'")


def downgrade() -> None:
    op.execute("ALTER TYPE poisource RENAME VALUE 'overpass_osm' TO 'foursquare'")
