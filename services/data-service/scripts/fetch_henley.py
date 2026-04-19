"""
Fetch Henley Passport Index visa matrix and save to data/raw/henley_passport_index.csv

Sources tried in order:
1. ACAMAR visa opendata (GitHub) - open dataset based on Henley/IATA data
2. Adam Chlipala's passport-index (GitHub) - CC0 public domain

Usage:
    python scripts/fetch_henley.py
"""

import csv
import logging
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "henley_passport_index.csv"
)

# Public domain passport index dataset - CC0 license
# Source: https://github.com/ilyankou/passport-index-dataset
PASSPORT_INDEX_URL = "https://raw.githubusercontent.com/ilyankou/passport-index-dataset/master/passport-index-matrix-iso2.csv"


def fetch_passport_matrix() -> list[list[str]]:
    """Fetch the passport index matrix CSV from GitHub."""
    headers = {"User-Agent": "TriplyDataBot/1.0 (travel-planner ETL)"}
    with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as client:
        resp = client.get(PASSPORT_INDEX_URL)
        resp.raise_for_status()
        return resp.text

    return ""


# Map passport index values to our schema
# -1 = no admission, 0 = visa required, 1 = visa on arrival/e-visa, 2+ = days visa-free
VALUE_MAP = {
    "-1": "NA",  # no admission
    "0": "VR",  # visa required
    "1": "VOA",  # visa on arrival / e-visa
}


def convert_value(val: str) -> str:
    """Convert passport-index numeric value to our VF/VOA/VR/NA format."""
    val = val.strip()
    if val in VALUE_MAP:
        return VALUE_MAP[val]
    try:
        days = int(val)
        if days > 0:
            return str(days)  # visa-free with stay limit (number of days)
    except ValueError:
        pass
    return "VR"  # default: visa required


def main():
    logger.info(
        "Fetching passport index matrix from GitHub (ilyankou/passport-index-dataset)..."
    )
    raw_csv = fetch_passport_matrix()

    if not raw_csv:
        logger.error("Failed to fetch passport matrix")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = raw_csv.strip().split("\n")
    reader = csv.reader(lines)
    rows = list(reader)

    if not rows:
        logger.error("Empty CSV data")
        return

    header = rows[0]  # First row: "", "AF", "AL", "DZ", ...
    logger.info(
        f"Matrix dimensions: {len(rows) - 1} citizenships × {len(header) - 1} destinations"
    )

    # Convert values and write with our format
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header (first cell = empty, rest = destination ISO2 codes)
        writer.writerow(header)

        for row in rows[1:]:
            if not row:
                continue
            new_row = [row[0]]  # citizenship ISO2
            for val in row[1:]:
                new_row.append(convert_value(val))
            writer.writerow(new_row)

    logger.info(f"Saved passport index matrix to {OUTPUT_PATH}")
    logger.info(
        f"Matrix: {len(rows) - 1} citizenships × {len(header) - 1} destinations = {(len(rows) - 1) * (len(header) - 1):,} visa rules"
    )


if __name__ == "__main__":
    main()
