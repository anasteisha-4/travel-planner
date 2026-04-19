"""Metro system city index — static CSV source.

Primary source: data/raw/metro_systems.csv (~170 systems, manually curated)

Note on Wikidata: Q928830 (metro system) P276 property points to city districts/stations,
not city names — making it unsuitable for city-level matching without deep P131 traversal
(which times out on the SPARQL endpoint). Static CSV is more reliable for this use case.

Returns {country_code: set(city_name_lower)} for matching against destinations.
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
METRO_CSV = DATA_DIR / "metro_systems.csv"


def build_metro_index(use_wikidata: bool = False) -> dict[str, set[str]]:
    """Load metro index from CSV → {country_code: set(city_name_lower)}.

    use_wikidata parameter kept for API compatibility but has no effect —
    Wikidata Q928830/P276 returns districts/stations, not cities.
    """
    if use_wikidata:
        logger.info(
            "Note: Wikidata metro enrichment is not supported (P276 returns districts, not cities). Using CSV only."
        )

    if not METRO_CSV.exists():
        logger.warning(f"metro_systems.csv not found at {METRO_CSV}")
        return {}

    index: dict[str, set[str]] = {}
    with open(METRO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cc = (row.get("country_code") or "").upper().strip()
            city = (row.get("city_name") or "").strip().lower()
            if cc and city:
                index.setdefault(cc, set()).add(city)

    total = sum(len(v) for v in index.values())
    logger.info(f"Loaded metro_systems.csv: {total} cities in {len(index)} countries")
    return index


if __name__ == "__main__":
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")
    index = build_metro_index()
    print(
        f"\nMetro index: {sum(len(v) for v in index.values())} cities in {len(index)} countries"
    )
    for cc in ["DE", "FR", "US", "RU", "JP", "ES", "IT", "GB", "CN", "BR", "IN"]:
        print(f"  {cc}: {sorted(index.get(cc, set()))}")
