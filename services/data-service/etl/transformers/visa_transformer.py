"""Transform Passport Index data (ilyankou/passport-index-dataset) into visa_rule rows.

Source values → VisaType mapping:
  visa free / numeric days  → visa_free  (score 1.0)
  visa on arrival           → evisa      (score 0.6)
  e-visa                    → evisa      (score 0.6)
  eta                       → evisa      (score 0.6)
  visa required             → visa_required (score 0.2)
  no admission              → no_admission  (score 0.0)
  -1                        → visa_free  (self-travel, skip or score 1.0)
"""

import logging

import pandas as pd

from app.models.visa import VisaType, VISA_SCORES

logger = logging.getLogger(__name__)

RAW_TO_VISA_TYPE: dict[str, VisaType] = {
    "visa free": VisaType.visa_free,
    "visa on arrival": VisaType.evisa,
    "e-visa": VisaType.evisa,
    "eta": VisaType.evisa,
    "visa required": VisaType.visa_required,
    "no admission": VisaType.no_admission,
}


def _get_country_destinations() -> dict[str, list[str]]:
    """Return {country_code_upper: [destination_id, ...]}"""
    from app.database import SessionLocal
    from app.models import Destination

    db = SessionLocal()
    try:
        destinations = db.query(Destination).all()
        result: dict[str, list[str]] = {}
        for d in destinations:
            result.setdefault(d.country_code.upper(), []).append(str(d.id))
        return result
    finally:
        db.close()


def transform_visa(df: pd.DataFrame) -> list[dict]:
    """Convert tidy 3-column passport index to visa_rule rows fanned out to destination_ids."""
    country_map = _get_country_destinations()
    records = []
    skipped_unknown = 0

    for _, row in df.iterrows():
        citizenship_code = str(row["passport_code"]).strip().upper()[:2]
        dest_country_code = str(row["destination_code"]).strip().upper()
        requirement = str(row["requirement"]).strip().lower()

        # Self-travel (-1) → visa_free (citizens enter home country freely)
        if requirement == "-1":
            visa_type = VisaType.visa_free
            max_stay_days = None
        else:
            visa_type = RAW_TO_VISA_TYPE.get(requirement)
            max_stay_days = None

            if visa_type is None:
                # Numeric = visa-free with stay limit in days
                try:
                    days = float(requirement)
                    if days > 0:
                        max_stay_days = int(days)
                        visa_type = VisaType.visa_free
                    else:
                        skipped_unknown += 1
                        continue
                except ValueError:
                    logger.debug(
                        f"Unknown requirement '{requirement}' for {citizenship_code} → {dest_country_code}"
                    )
                    skipped_unknown += 1
                    continue

        dest_ids = country_map.get(dest_country_code, [])
        for dest_id in dest_ids:
            records.append(
                {
                    "citizenship_code": citizenship_code,
                    "destination_id": dest_id,
                    "visa_type": visa_type.value,
                    "visa_score": VISA_SCORES[visa_type],
                    "max_stay_days": max_stay_days,
                    "data_year": 2025,
                }
            )

    if skipped_unknown:
        logger.debug(
            f"Skipped {skipped_unknown} rows with unrecognized requirement values."
        )
    logger.info(f"Transformed {len(records)} visa rule records.")
    return records
