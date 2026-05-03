"""Load IATA airport lookup data from an OurAirports CSV snapshot."""

from __future__ import annotations

import argparse
import csv
import uuid
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Airport

AIRPORT_TYPE_WEIGHT = {"large_airport", "medium_airport", "small_airport"}


def _iter_airports(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iata = (row.get("iata_code") or "").strip().upper()
            airport_type = (row.get("type") or "").strip()
            if not iata or airport_type not in AIRPORT_TYPE_WEIGHT:
                continue
            scheduled = (row.get("scheduled_service") or "").strip().lower() == "yes"
            if airport_type == "small_airport" and not scheduled:
                continue
            try:
                lat = float(row.get("latitude_deg") or "")
                lng = float(row.get("longitude_deg") or "")
            except ValueError:
                continue
            yield {
                "id": uuid.uuid4(),
                "iata_code": iata,
                "ident": (row.get("ident") or "").strip() or None,
                "airport_type": airport_type,
                "name": (row.get("name") or "").strip(),
                "municipality": (row.get("municipality") or "").strip() or None,
                "country_code": (row.get("iso_country") or "").strip().upper(),
                "lat": lat,
                "lng": lng,
                "scheduled_service": scheduled,
            }


def load_airports(path: Path) -> int:
    rows = list(_iter_airports(path))
    if not rows:
        return 0

    db = SessionLocal()
    try:
        stmt = insert(Airport).values(rows)
        update_cols = {
            "ident": stmt.excluded.ident,
            "airport_type": stmt.excluded.airport_type,
            "name": stmt.excluded.name,
            "municipality": stmt.excluded.municipality,
            "country_code": stmt.excluded.country_code,
            "lat": stmt.excluded.lat,
            "lng": stmt.excluded.lng,
            "scheduled_service": stmt.excluded.scheduled_service,
        }
        db.execute(stmt.on_conflict_do_update(index_elements=[Airport.iata_code], set_=update_cols))
        db.commit()
        return len(rows)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    count = load_airports(args.csv_path)
    print(f"Loaded {count} airports")


if __name__ == "__main__":
    main()
