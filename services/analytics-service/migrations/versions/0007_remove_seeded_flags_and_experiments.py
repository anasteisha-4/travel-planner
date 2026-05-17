"""Remove seeded flags and experiments

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-17

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM analytics_experiment_assignments WHERE experiment_key IN ("
        "'ranker_content_vs_hybrid_v2', "
        "'recommendation_explanation_ui', "
        "'destination_validation_placement', "
        "'budget_uncertainty_ui', "
        "'itinerary_generation_entry'"
        ")"
    )
    op.execute(
        "DELETE FROM experiments WHERE key IN ("
        "'ranker_content_vs_hybrid_v2', "
        "'recommendation_explanation_ui', "
        "'destination_validation_placement', "
        "'budget_uncertainty_ui', "
        "'itinerary_generation_entry'"
        ") AND description = 'Seeded Triply experiment'"
    )
    op.execute(
        "DELETE FROM feature_flags WHERE key IN ("
        "'analytics_collection_enabled', "
        "'hybrid_ranker_v2_enabled', "
        "'behavioral_ltr_augmentation_enabled', "
        "'budget_monitor_ml_enabled', "
        "'itinerary_ranker_enabled', "
        "'itinerary_dnd_enabled', "
        "'travel_fare_enrichment_enabled', "
        "'destination_validation_block_enabled'"
        ") AND description = 'Seeded analytics platform flag'"
    )


def downgrade() -> None:
    pass
