"""Apply a portable Russian destination-name seed to name_translations.

The script is idempotent. It resolves destinations by UUID first and then by
the stable source key `(name, country_code)`, so the seed remains usable if a
database was restored with different UUIDs but the destination catalog is the
same.

Example:
  python scripts/apply_destination_name_translations.py --require-all-active
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.models import Destination, NameTranslation, NameTranslationEntity, NameTranslationQuality
from app.services.name_translation_service import is_usable_destination_translation

DEFAULT_INPUT = Path("/app/data/seed/destination_name_translations_ru.json")


def _load_seed(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text())
    if document.get("schema_version") != 1:
        raise ValueError(f"Unsupported seed schema_version: {document.get('schema_version')}")
    if document.get("entity_type") != "destination" or document.get("locale") != "ru":
        raise ValueError("Seed must contain Russian destination translations")
    rows = document.get("translations")
    if not isinstance(rows, list):
        raise ValueError("Seed translations must be a list")
    return rows


def _coerce_quality(value: str | None) -> NameTranslationQuality:
    if value:
        try:
            return NameTranslationQuality(value)
        except ValueError:
            pass
    return NameTranslationQuality.authoritative


def _resolve_destination(
    destinations_by_id: dict[str, Destination],
    destinations_by_name_country: dict[tuple[str, str], Destination],
    row: dict[str, Any],
) -> Destination | None:
    destination_id = row.get("destination_id")
    if destination_id and destination_id in destinations_by_id:
        return destinations_by_id[destination_id]
    name = row.get("destination_name")
    country_code = row.get("country_code")
    if name and country_code:
        return destinations_by_name_country.get((name, country_code))
    return None


def apply_translations(path: Path, *, dry_run: bool, require_all_active: bool) -> dict[str, int]:
    seed_rows = _load_seed(path)

    with SessionLocal() as db:
        destinations = db.query(Destination).all()
        destinations_by_id = {str(destination.id): destination for destination in destinations}
        destinations_by_name_country = {
            (destination.name, destination.country_code): destination for destination in destinations
        }

        payload = []
        unresolved_seed_rows = 0
        skipped_invalid = 0
        for row in seed_rows:
            destination = _resolve_destination(destinations_by_id, destinations_by_name_country, row)
            if destination is None:
                unresolved_seed_rows += 1
                continue

            translated_name = row.get("translated_name")
            provider = row.get("provider") or "seed"
            if not is_usable_destination_translation(destination.name, translated_name, provider):
                skipped_invalid += 1
                continue

            payload.append(
                {
                    "id": uuid.uuid4(),
                    "entity_type": NameTranslationEntity.destination,
                    "entity_id": destination.id,
                    "locale": "ru",
                    "original_name": destination.name,
                    "translated_name": translated_name,
                    "provider": provider,
                    "provider_ref": row.get("provider_ref"),
                    "quality": _coerce_quality(row.get("quality")),
                    "confidence": float(row.get("confidence") or 1.0),
                    "translation_metadata": row.get("translation_metadata") or {},
                }
            )

        active_destination_ids = {str(destination.id) for destination in destinations if destination.is_active}
        covered_active_ids = {
            str(row["entity_id"]) for row in payload if str(row["entity_id"]) in active_destination_ids
        }
        missing_active = len(active_destination_ids - covered_active_ids)

        if require_all_active and missing_active:
            raise RuntimeError(f"Seed does not cover {missing_active} active destinations")

        if payload and not dry_run:
            stmt = insert(NameTranslation).values(payload)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_name_translation_entity_locale",
                set_={
                    "original_name": stmt.excluded.original_name,
                    "translated_name": stmt.excluded.translated_name,
                    "provider": stmt.excluded.provider,
                    "provider_ref": stmt.excluded.provider_ref,
                    "quality": stmt.excluded.quality,
                    "confidence": stmt.excluded.confidence,
                    "translation_metadata": stmt.excluded.translation_metadata,
                    "updated_at": text("now()"),
                },
            )
            db.execute(stmt)
            db.commit()

        return {
            "loaded": len(seed_rows),
            "upserted": len(payload),
            "unresolved_seed_rows": unresolved_seed_rows,
            "skipped_invalid": skipped_invalid,
            "missing_active": missing_active,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Russian destination translation seed.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-all-active", action="store_true")
    args = parser.parse_args()

    stats = apply_translations(args.input, dry_run=args.dry_run, require_all_active=args.require_all_active)
    prefix = "dry-run " if args.dry_run else ""
    print(
        f"{prefix}destination translation seed applied "
        f"input={args.input} loaded={stats['loaded']} upserted={stats['upserted']} "
        f"unresolved_seed_rows={stats['unresolved_seed_rows']} skipped_invalid={stats['skipped_invalid']} "
        f"missing_active={stats['missing_active']}"
    )


if __name__ == "__main__":
    main()
