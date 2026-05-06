import uuid

from sqlalchemy.orm import Session

from app.lib.russian_names import translate_destination_name, translate_poi_name
from app.models import NameTranslation, NameTranslationEntity


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


def destination_display_payload(
    destination_id: str, original_name: str, translations: dict[str, NameTranslation]
) -> dict:
    row = translations.get(destination_id)
    translated = row.translated_name if row else translate_destination_name(original_name)
    return {
        "name": translated,
        "name_original": original_name,
        "name_ru": translated,
        "display_name": translated,
        "name_translation_quality": row.quality.value if row else "fallback",
        "name_translation_provider": row.provider if row else "local_rules",
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
