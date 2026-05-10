"""Export safe Russian destination names into a portable seed file.

This script reads the current database overlay and writes a deterministic JSON
file that can be copied to production and applied without calling external
providers.

Example:
  python scripts/export_destination_name_translations.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.lib.russian_names import has_cyrillic, translate_destination_name
from app.models import Destination, NameTranslation, NameTranslationEntity
from app.services.name_translation_service import is_usable_destination_translation

DEFAULT_OUTPUT = Path("/app/data/seed/destination_name_translations_ru.json")


def _translation_payload(destination: Destination, row: NameTranslation | None) -> dict[str, Any] | None:
    if row and is_usable_destination_translation(destination.name, row.translated_name, row.provider):
        return {
            "destination_id": str(destination.id),
            "destination_name": destination.name,
            "country_code": destination.country_code,
            "translated_name": row.translated_name,
            "provider": row.provider,
            "provider_ref": row.provider_ref,
            "quality": row.quality.value,
            "confidence": row.confidence,
            "translation_metadata": row.translation_metadata or {},
        }

    local_name = translate_destination_name(destination.name)
    if local_name and local_name != destination.name and has_cyrillic(local_name):
        return {
            "destination_id": str(destination.id),
            "destination_name": destination.name,
            "country_code": destination.country_code,
            "translated_name": local_name,
            "provider": "local_curated",
            "provider_ref": None,
            "quality": "manual",
            "confidence": 1.0,
            "translation_metadata": {"source": "local_curated_export"},
        }

    return None


def export_translations(output: Path, include_inactive: bool) -> dict[str, int]:
    with SessionLocal() as db:
        query = db.query(Destination).order_by(Destination.country_code, Destination.name)
        if not include_inactive:
            query = query.filter(Destination.is_active.is_(True))
        destinations = query.all()

        translations = {
            str(row.entity_id): row
            for row in db.query(NameTranslation)
            .filter(
                NameTranslation.entity_type == NameTranslationEntity.destination,
                NameTranslation.locale == "ru",
            )
            .all()
        }

        rows = []
        missing = 0
        for destination in destinations:
            payload = _translation_payload(destination, translations.get(str(destination.id)))
            if payload is None:
                missing += 1
                continue
            rows.append(payload)

    document = {
        "schema_version": 1,
        "entity_type": "destination",
        "locale": "ru",
        "generated_at": datetime.now(UTC).isoformat(),
        "translations": rows,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"exported": len(rows), "missing": missing, "total": len(destinations)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export safe Russian destination translation seed.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-inactive", action="store_true")
    args = parser.parse_args()

    stats = export_translations(args.output, args.include_inactive)
    print(
        "destination translation seed exported "
        f"path={args.output} exported={stats['exported']} missing={stats['missing']} total={stats['total']}"
    )


if __name__ == "__main__":
    main()
