import uuid

from sqlalchemy.orm import Session

from app.lib.russian_names import has_cyrillic, translate_destination_name, translate_poi_name
from app.models import NameTranslation, NameTranslationEntity

DESTINATION_BAD_TRANSLATION_MARKERS = (
    "значения",
    "не путать",
)


def load_translations(
    db: Session,
    entity_type: NameTranslationEntity,
    entity_ids: list[uuid.UUID],
    locale: str = "ru",
) -> dict[str, NameTranslation]:
    if not entity_ids:
        return {}
    rows = (
        db.query(NameTranslation)
        .filter(
            NameTranslation.entity_type == entity_type,
            NameTranslation.locale == locale,
            NameTranslation.entity_id.in_(entity_ids),
        )
        .all()
    )
    return {str(row.entity_id): row for row in rows}


def is_usable_destination_translation(original_name: str, translated_name: str | None, provider: str | None) -> bool:
    if not translated_name or translated_name == original_name:
        return False
    if not has_cyrillic(translated_name):
        return False
    normalized = translated_name.casefold()
    if any(marker in normalized for marker in DESTINATION_BAD_TRANSLATION_MARKERS):
        return False
    if "(" in translated_name or ")" in translated_name:
        return False
    return provider != "nominatim_reverse_ru"


def resolve_destination_display_name(
    original_name: str,
    row: NameTranslation | None,
) -> tuple[str, str, str]:
    if row and is_usable_destination_translation(original_name, row.translated_name, row.provider):
        return row.translated_name, row.quality.value, row.provider

    local_name = translate_destination_name(original_name)
    if local_name and local_name != original_name and has_cyrillic(local_name):
        return local_name, "manual", "local_rules"

    return original_name, "fallback", "original"


def destination_display_payload(
    destination_id: str, original_name: str, translations: dict[str, NameTranslation]
) -> dict:
    row = translations.get(destination_id)
    translated, quality, provider = resolve_destination_display_name(original_name, row)
    return {
        "name": translated,
        "name_original": original_name,
        "name_ru": translated,
        "display_name": translated,
        "name_translation_quality": quality,
        "name_translation_provider": provider,
    }


def poi_display_payload(poi_id: str, original_name: str, translations: dict[str, NameTranslation]) -> dict:
    row = translations.get(poi_id)
    translated = row.translated_name if row else translate_poi_name(original_name)
    return {
        "name": translated,
        "name_original": original_name,
        "name_ru": translated,
        "display_name": translated,
        "name_translation_quality": row.quality.value if row else "fallback",
        "name_translation_provider": row.provider if row else "local_rules",
    }
