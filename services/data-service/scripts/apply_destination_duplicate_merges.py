"""Apply curated destination duplicate merges.

The script is idempotent and intended for production deploys. It rewrites
destination references before deleting duplicate destination rows, so dependent
POI, feature tables, training rows, trips, analytics and cached logs keep
pointing to a live canonical destination.

Example:
  python scripts/apply_destination_duplicate_merges.py --dry-run
  python scripts/apply_destination_duplicate_merges.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, "/app")

from app.database import SessionLocal

DEFAULT_INPUT = Path("/app/data/seed/destination_duplicate_merges.json")

ONE_TO_ONE_TABLES = (
    "destination_costs",
    "destination_safety",
    "destination_attributes",
    "destination_connectivity",
    "destination_language_accessibility",
    "destination_infrastructure",
)

DIRECT_REFERENCE_TABLES = (
    "poi",
    "destination_events",
    "trajectories",
    "trip_budget_actuals",
    "ltr_training_pairs",
    "user_preference_profiles",
)

DIRECT_OPTIONAL_REFERENCE_TABLES = (
    ("trips", "destination_id"),
    ("user_preference_profiles", "label_destination_id"),
)


def _load_seed(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text())
    if document.get("version") != 1:
        raise ValueError(f"Unsupported duplicate merge seed version: {document.get('version')}")
    merges = document.get("merges")
    if not isinstance(merges, list):
        raise ValueError("Duplicate merge seed must contain a merges list")
    return merges


def _validate_uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar())


def _destination_exists(db: Session, destination_id: str) -> bool:
    return bool(
        db.execute(
            text("SELECT 1 FROM destinations WHERE id = :destination_id"),
            {"destination_id": destination_id},
        ).first()
    )


def _execute(db: Session, sql: str, params: dict[str, Any], stats: dict[str, int], key: str) -> None:
    result = db.execute(text(sql), params)
    stats[key] = stats.get(key, 0) + int(result.rowcount or 0)


def _merge_one_to_one_table(
    db: Session, table_name: str, canonical_id: str, duplicate_id: str, stats: dict[str, int]
) -> None:
    if not _table_exists(db, table_name):
        return
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    _execute(
        db,
        f"""
        UPDATE {table_name} duplicate_row
        SET destination_id = :canonical_id
        WHERE duplicate_row.destination_id = :duplicate_id
          AND NOT EXISTS (
            SELECT 1 FROM {table_name} canonical_row
            WHERE canonical_row.destination_id = :canonical_id
          )
        """,
        params,
        stats,
        f"{table_name}_moved",
    )
    _execute(
        db,
        f"DELETE FROM {table_name} WHERE destination_id = :duplicate_id",
        params,
        stats,
        f"{table_name}_deleted_conflicts",
    )


def _merge_activity_rows(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    _execute(
        db,
        """
        UPDATE destination_activities canonical_row
        SET
          score = GREATEST(canonical_row.score, duplicate_row.score),
          poi_count = canonical_row.poi_count + duplicate_row.poi_count,
          updated_at = now()
        FROM destination_activities duplicate_row
        WHERE canonical_row.destination_id = :canonical_id
          AND duplicate_row.destination_id = :duplicate_id
          AND canonical_row.activity_type = duplicate_row.activity_type
        """,
        params,
        stats,
        "destination_activities_merged_conflicts",
    )
    _execute(
        db,
        """
        UPDATE destination_activities duplicate_row
        SET destination_id = :canonical_id
        WHERE duplicate_row.destination_id = :duplicate_id
          AND NOT EXISTS (
            SELECT 1 FROM destination_activities canonical_row
            WHERE canonical_row.destination_id = :canonical_id
              AND canonical_row.activity_type = duplicate_row.activity_type
          )
        """,
        params,
        stats,
        "destination_activities_moved",
    )
    _execute(
        db,
        "DELETE FROM destination_activities WHERE destination_id = :duplicate_id",
        params,
        stats,
        "destination_activities_deleted_conflicts",
    )


def _merge_monthly_table(
    db: Session,
    table_name: str,
    canonical_id: str,
    duplicate_id: str,
    stats: dict[str, int],
) -> None:
    if not _table_exists(db, table_name):
        return
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    if table_name == "destination_popularity":
        _execute(
            db,
            """
            UPDATE destination_popularity canonical_row
            SET
              avg_pageviews = GREATEST(canonical_row.avg_pageviews, duplicate_row.avg_pageviews),
              crowd_index = GREATEST(canonical_row.crowd_index, duplicate_row.crowd_index),
              wikipedia_article = COALESCE(canonical_row.wikipedia_article, duplicate_row.wikipedia_article),
              data_year = COALESCE(canonical_row.data_year, duplicate_row.data_year),
              updated_at = now()
            FROM destination_popularity duplicate_row
            WHERE canonical_row.destination_id = :canonical_id
              AND duplicate_row.destination_id = :duplicate_id
              AND canonical_row.month = duplicate_row.month
            """,
            params,
            stats,
            "destination_popularity_merged_conflicts",
        )
    _execute(
        db,
        f"""
        UPDATE {table_name} duplicate_row
        SET destination_id = :canonical_id
        WHERE duplicate_row.destination_id = :duplicate_id
          AND NOT EXISTS (
            SELECT 1 FROM {table_name} canonical_row
            WHERE canonical_row.destination_id = :canonical_id
              AND canonical_row.month = duplicate_row.month
          )
        """,
        params,
        stats,
        f"{table_name}_moved",
    )
    _execute(
        db,
        f"DELETE FROM {table_name} WHERE destination_id = :duplicate_id",
        params,
        stats,
        f"{table_name}_deleted_conflicts",
    )


def _merge_visa_rules(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    _execute(
        db,
        """
        UPDATE visa_rules canonical_row
        SET
          visa_score = GREATEST(canonical_row.visa_score, duplicate_row.visa_score),
          max_stay_days = GREATEST(
            COALESCE(canonical_row.max_stay_days, 0),
            COALESCE(duplicate_row.max_stay_days, 0)
          ),
          notes = COALESCE(canonical_row.notes, duplicate_row.notes),
          data_year = GREATEST(COALESCE(canonical_row.data_year, 0), COALESCE(duplicate_row.data_year, 0))
        FROM visa_rules duplicate_row
        WHERE canonical_row.destination_id = :canonical_id
          AND duplicate_row.destination_id = :duplicate_id
          AND canonical_row.citizenship_code = duplicate_row.citizenship_code
        """,
        params,
        stats,
        "visa_rules_merged_conflicts",
    )
    _execute(
        db,
        """
        UPDATE visa_rules duplicate_row
        SET destination_id = :canonical_id
        WHERE duplicate_row.destination_id = :duplicate_id
          AND NOT EXISTS (
            SELECT 1 FROM visa_rules canonical_row
            WHERE canonical_row.destination_id = :canonical_id
              AND canonical_row.citizenship_code = duplicate_row.citizenship_code
          )
        """,
        params,
        stats,
        "visa_rules_moved",
    )
    _execute(
        db,
        "DELETE FROM visa_rules WHERE destination_id = :duplicate_id",
        params,
        stats,
        "visa_rules_deleted_conflicts",
    )


def _merge_name_translations(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    _execute(
        db,
        """
        UPDATE name_translations duplicate_row
        SET entity_id = :canonical_id
        WHERE duplicate_row.entity_type = 'destination'
          AND duplicate_row.entity_id = :duplicate_id
          AND NOT EXISTS (
            SELECT 1 FROM name_translations canonical_row
            WHERE canonical_row.entity_type = 'destination'
              AND canonical_row.entity_id = :canonical_id
              AND canonical_row.locale = duplicate_row.locale
          )
        """,
        params,
        stats,
        "name_translations_moved",
    )
    _execute(
        db,
        """
        DELETE FROM name_translations
        WHERE entity_type = 'destination'
          AND entity_id = :duplicate_id
        """,
        params,
        stats,
        "name_translations_deleted_conflicts",
    )


def _merge_direct_references(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    for table_name in DIRECT_REFERENCE_TABLES:
        if not _table_exists(db, table_name):
            continue
        column = "label_destination_id" if table_name == "user_preference_profiles" else "destination_id"
        _execute(
            db,
            f"UPDATE {table_name} SET {column} = :canonical_id WHERE {column} = :duplicate_id",
            {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
            stats,
            f"{table_name}_{column}_updated",
        )
    for table_name, column in DIRECT_OPTIONAL_REFERENCE_TABLES:
        if not _table_exists(db, table_name):
            continue
        _execute(
            db,
            f"UPDATE {table_name} SET {column} = :canonical_id WHERE {column} = :duplicate_id",
            {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
            stats,
            f"{table_name}_{column}_updated",
        )


def _merge_text_arrays(
    db: Session, table_name: str, columns: tuple[str, ...], canonical_id: str, duplicate_id: str, stats: dict[str, int]
) -> None:
    if not _table_exists(db, table_name):
        return
    for column in columns:
        _execute(
            db,
            f"""
            UPDATE {table_name}
            SET {column} = ARRAY(
              SELECT mapped
              FROM (
                SELECT
                  CASE WHEN value = :duplicate_id THEN :canonical_id ELSE value END AS mapped,
                  MIN(ord) AS first_ord
                FROM unnest({column}) WITH ORDINALITY AS items(value, ord)
                GROUP BY mapped
                ORDER BY MIN(ord)
              ) deduped
            )
            WHERE :duplicate_id = ANY({column})
            """,
            {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
            stats,
            f"{table_name}_{column}_updated",
        )


def _merge_json_text_references(
    db: Session,
    table_name: str,
    columns: tuple[str, ...],
    canonical_id: str,
    duplicate_id: str,
    stats: dict[str, int],
) -> None:
    if not _table_exists(db, table_name):
        return
    for column in columns:
        _execute(
            db,
            f"""
            UPDATE {table_name}
            SET {column} = replace({column}::text, :duplicate_id, :canonical_id)::jsonb
            WHERE {column}::text LIKE '%' || :duplicate_id || '%'
            """,
            {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
            stats,
            f"{table_name}_{column}_json_updated",
        )


def _merge_user_events(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    if not _table_exists(db, "user_events"):
        return
    params = {"canonical_id": canonical_id, "duplicate_id": duplicate_id}
    _execute(
        db,
        """
        UPDATE user_events
        SET entity_id = :canonical_id
        WHERE entity_type = 'destination'
          AND entity_id = :duplicate_id
        """,
        params,
        stats,
        "user_events_entity_id_updated",
    )
    _merge_json_text_references(db, "user_events", ("context", "client_meta"), canonical_id, duplicate_id, stats)


def _merge_destination_metadata(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    _execute(
        db,
        """
        UPDATE destinations canonical_row
        SET
          capital = canonical_row.capital OR duplicate_row.capital,
          population = GREATEST(COALESCE(canonical_row.population, 0), COALESCE(duplicate_row.population, 0)),
          radius_m = GREATEST(canonical_row.radius_m, duplicate_row.radius_m),
          currencies = COALESCE(canonical_row.currencies, '{}'::jsonb) || COALESCE(duplicate_row.currencies, '{}'::jsonb),
          updated_at = now()
        FROM destinations duplicate_row
        WHERE canonical_row.id = :canonical_id
          AND duplicate_row.id = :duplicate_id
        """,
        {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
        stats,
        "destinations_metadata_merged",
    )


def _delete_duplicate_destination(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    _execute(
        db,
        "DELETE FROM destinations WHERE id = :duplicate_id AND id <> :canonical_id",
        {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
        stats,
        "destinations_deleted",
    )


def _apply_one_merge(db: Session, canonical_id: str, duplicate_id: str, stats: dict[str, int]) -> None:
    if canonical_id == duplicate_id:
        raise ValueError(f"Canonical and duplicate ids are the same: {canonical_id}")
    if not _destination_exists(db, canonical_id):
        raise RuntimeError(f"Canonical destination does not exist: {canonical_id}")
    if not _destination_exists(db, duplicate_id):
        stats["duplicates_already_absent"] = stats.get("duplicates_already_absent", 0) + 1
        return

    for table_name in ONE_TO_ONE_TABLES:
        _merge_one_to_one_table(db, table_name, canonical_id, duplicate_id, stats)
    _merge_activity_rows(db, canonical_id, duplicate_id, stats)
    _merge_monthly_table(db, "destination_seasonality", canonical_id, duplicate_id, stats)
    _merge_monthly_table(db, "destination_popularity", canonical_id, duplicate_id, stats)
    _merge_visa_rules(db, canonical_id, duplicate_id, stats)
    _merge_name_translations(db, canonical_id, duplicate_id, stats)
    _merge_direct_references(db, canonical_id, duplicate_id, stats)
    _merge_text_arrays(
        db,
        "user_profiles",
        ("liked_destination_ids",),
        canonical_id,
        duplicate_id,
        stats,
    )
    _merge_text_arrays(
        db,
        "user_features",
        ("viewed_destination_ids", "clicked_destination_ids", "visited_destination_ids"),
        canonical_id,
        duplicate_id,
        stats,
    )
    _merge_user_events(db, canonical_id, duplicate_id, stats)
    _merge_json_text_references(
        db, "recommendation_logs", ("request", "scorer_weights", "results"), canonical_id, duplicate_id, stats
    )
    _merge_destination_metadata(db, canonical_id, duplicate_id, stats)
    _delete_duplicate_destination(db, canonical_id, duplicate_id, stats)
    stats["merge_pairs_applied"] = stats.get("merge_pairs_applied", 0) + 1


def apply_duplicate_merges(path: Path, *, dry_run: bool) -> dict[str, int]:
    seed_merges = _load_seed(path)
    stats: dict[str, int] = {"merge_groups_loaded": len(seed_merges)}
    seen_duplicates: set[str] = set()
    seen_canonicals: set[str] = set()

    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('destination_duplicate_merges_v1'))"))
        for group in seed_merges:
            canonical_id = _validate_uuid(group.get("canonical_id"), "canonical_id")
            if canonical_id in seen_duplicates:
                raise RuntimeError(f"Canonical id is also listed as duplicate in an earlier group: {canonical_id}")
            seen_canonicals.add(canonical_id)
            duplicate_ids = group.get("duplicate_ids")
            if not isinstance(duplicate_ids, list) or not duplicate_ids:
                raise ValueError(f"Merge group for {canonical_id} has no duplicate_ids")
            for raw_duplicate_id in duplicate_ids:
                duplicate_id = _validate_uuid(raw_duplicate_id, "duplicate_id")
                if duplicate_id in seen_canonicals:
                    raise RuntimeError(f"Duplicate id is also listed as canonical in an earlier group: {duplicate_id}")
                if duplicate_id in seen_duplicates:
                    raise RuntimeError(f"Duplicate id is listed more than once: {duplicate_id}")
                seen_duplicates.add(duplicate_id)
                _apply_one_merge(db, canonical_id, duplicate_id, stats)

        if dry_run:
            db.rollback()
        else:
            db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply curated destination duplicate merges.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = apply_duplicate_merges(args.input, dry_run=args.dry_run)
    mode = "dry-run" if args.dry_run else "applied"
    rendered_stats = " ".join(f"{key}={value}" for key, value in sorted(stats.items()))
    print(f"destination duplicate merges {mode} input={args.input} {rendered_stats}")


if __name__ == "__main__":
    main()
