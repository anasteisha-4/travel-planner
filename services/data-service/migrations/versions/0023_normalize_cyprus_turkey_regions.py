"""Normalize Cyprus and Turkey destination regions.

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-18
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE destinations
        SET region = 'Europe', subregion = 'Southern Europe', updated_at = NOW()
        WHERE upper(country_code) = 'CY'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE destinations
        SET region = 'Asia', subregion = 'Western Asia', updated_at = NOW()
        WHERE upper(country_code) = 'CY'
        """
    )
