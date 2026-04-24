"""add user_profiles table

Revision ID: e91dd317f15e
Revises: c1a2b3d4e5f6
Create Date: 2026-04-19 20:23:58.411166

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e91dd317f15e'
down_revision: Union[str, Sequence[str], None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('vacation_preferences_ranked', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('preferred_currency', sa.String(length=3), nullable=False, server_default='RUB'),
        sa.Column('budget_min', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('budget_max', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('budget_min_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('budget_max_usd', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('typical_duration', sa.String(length=20), nullable=True),
        sa.Column('typical_duration_days', sa.SmallInteger(), nullable=True),
        sa.Column('origin_city_id', sa.Integer(), nullable=True),
        sa.Column('origin_city_name', sa.Text(), nullable=True),
        sa.Column('origin_lat', sa.Float(), nullable=True),
        sa.Column('origin_lng', sa.Float(), nullable=True),
        sa.Column('liked_destination_ids', sa.ARRAY(sa.Integer()), nullable=True),
        sa.Column('risk_tolerance', sa.SmallInteger(), nullable=True),
        sa.Column('visa_tolerance', sa.String(length=20), nullable=True),
        sa.Column('language_comfort', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('crowd_preference', sa.SmallInteger(), nullable=True),
        sa.Column('climate_preferences', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('free_text_notes', sa.Text(), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('onboarding_step', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_user_profiles_liked_destination_ids', 'user_profiles', ['liked_destination_ids'], unique=False, postgresql_using='gin')
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=True)
    op.create_index('ix_user_profiles_vacation_preferences_ranked', 'user_profiles', ['vacation_preferences_ranked'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_user_profiles_vacation_preferences_ranked', table_name='user_profiles', postgresql_using='gin')
    op.drop_index('ix_user_profiles_user_id', table_name='user_profiles')
    op.drop_index('ix_user_profiles_liked_destination_ids', table_name='user_profiles', postgresql_using='gin')
    op.drop_table('user_profiles')
