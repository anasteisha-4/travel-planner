"""Legacy LLM quality placeholder

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-17

"""

from typing import Sequence, Union

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
