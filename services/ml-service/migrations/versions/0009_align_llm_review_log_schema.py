"""Align LLM review log schema

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-17

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_review_logs ADD COLUMN IF NOT EXISTS input_hash VARCHAR(128)")
    op.execute("UPDATE llm_review_logs SET input_hash = '' WHERE input_hash IS NULL")
    op.execute("ALTER TABLE llm_review_logs ALTER COLUMN input_hash SET NOT NULL")
    op.execute("ALTER TABLE llm_review_logs ADD COLUMN IF NOT EXISTS issue_codes JSONB")
    op.execute("UPDATE llm_review_logs SET issue_codes = '[]'::jsonb WHERE issue_codes IS NULL")
    op.execute("ALTER TABLE llm_review_logs ALTER COLUMN issue_codes SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_review_logs_input_hash ON llm_review_logs (input_hash)")


def downgrade() -> None:
    pass
