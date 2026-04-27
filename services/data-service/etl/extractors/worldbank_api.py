"""World Bank API extractor for infrastructure indicators.

Downloads country-level indicators and saves to CSV files in data/raw/.

Indicators used:
  SP.DYN.LE00.IN  — Life expectancy at birth (→ healthcare_score)
  LP.LPI.INFR.XQ  — LPI Infrastructure quality score (→ road_quality_score)
  FB.ATM.TOTL.P5  — ATM machines per 100,000 adults (→ atm_density_score)
  FX.OWN.TOTL.ZS  — Account ownership % (→ cash_economy proxy)

Usage:
  python -m etl.extractors.worldbank_api [--force]
"""

import csv
import json
import logging
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

_WB_BASE = "https://api.worldbank.org/v2/country/all/indicator"
_INDICATORS = {
    "healthcare": {
        "indicator": "SP.DYN.LE00.IN",
        "mrv": 5,
        "output": "healthcare_life_expectancy.csv",
        "fieldnames": [
            "country_code",
            "life_expectancy",
            "healthcare_score",
            "data_year",
        ],
    },
    "road_quality": {
        "indicator": "LP.LPI.INFR.XQ",
        "mrv": 10,
        "output": "road_quality_wef.csv",
        "fieldnames": [
            "country_code",
            "road_quality_score",
            "raw_lpi_score",
            "data_year",
        ],
    },
    "atm": {
        "indicator": "FB.ATM.TOTL.P5",
        "mrv": 5,
        "output": "atm_banking_access.csv",
        "fieldnames": [
            "country_code",
            "atm_density_proxy",
            "raw_atm_per_100k",
            "data_year",
        ],
    },
    "cash_economy": {
        "indicator": "FX.OWN.TOTL.ZS",
        "mrv": 5,
        "output": "cash_economy_findex.csv",
        "fieldnames": [
            "country_code",
            "percent_account_ownership",
            "is_cash_economy",
            "data_year",
        ],
    },
}


def _fetch_indicator(indicator: str, mrv: int) -> list[dict]:
    """Fetch all countries for a WB indicator. Returns raw WB records."""
    url = f"{_WB_BASE}/{indicator}?format=json&mrv={mrv}&per_page=20000"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                data = json.load(r)
            records = data[1] if len(data) > 1 else []
            logger.info(f"Fetched {len(records)} records for {indicator}")
            return records
        except Exception as e:
            logger.warning(f"WB API attempt {attempt + 1} failed for {indicator}: {e}")
            time.sleep(3)
    return []


def _is_real_country_code(iso2: str) -> bool:
    """Filter out World Bank aggregate codes (1A, Z4, XC, etc.)."""
    if len(iso2) != 2:
        return False
    if iso2[0].isdigit():
        return False
    # WB aggregate codes: start with X/Y/Z + digit, or S/B/8 combinations
    return not (iso2[0] in "XYZS" and iso2[1].isdigit())


def _latest_by_country(records: list[dict]) -> dict[str, tuple[float, str]]:
    """Extract latest non-null value per real country code → {iso2: (value, year)}."""
    result: dict[str, tuple[float, str]] = {}
    for rec in records:
        iso2 = (rec.get("country", {}).get("id") or "").strip()
        if not _is_real_country_code(iso2):
            continue
        val = rec.get("value")
        year = rec.get("date", "")
        if val is not None and iso2 not in result:
            result[iso2] = (float(val), year)
    return result


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_healthcare() -> int:
    """Download life expectancy and compute healthcare_score = (le - 50) / 35, clip [0, 1]."""
    cfg = _INDICATORS["healthcare"]
    records = _fetch_indicator(cfg["indicator"], cfg["mrv"])
    data = _latest_by_country(records)
    rows = []
    for cc, (le, year) in sorted(data.items()):
        score = round(max(0.0, min(1.0, (le - 50.0) / 35.0)), 4)
        rows.append(
            {
                "country_code": cc,
                "life_expectancy": round(le, 2),
                "healthcare_score": score,
                "data_year": year,
            }
        )
    _write_csv(DATA_DIR / cfg["output"], rows, cfg["fieldnames"])
    logger.info(f"healthcare: {len(rows)} countries → {cfg['output']}")
    return len(rows)


def extract_road_quality() -> int:
    """Download LPI Infrastructure score (1–5) → road_quality_score = (score - 1) / 4."""
    cfg = _INDICATORS["road_quality"]
    records = _fetch_indicator(cfg["indicator"], cfg["mrv"])
    data = _latest_by_country(records)
    rows = []
    for cc, (v, year) in sorted(data.items()):
        norm = round((v - 1.0) / 4.0, 4)
        rows.append(
            {
                "country_code": cc,
                "road_quality_score": norm,
                "raw_lpi_score": round(v, 4),
                "data_year": year,
            }
        )
    _write_csv(DATA_DIR / cfg["output"], rows, cfg["fieldnames"])
    logger.info(f"road_quality: {len(rows)} countries → {cfg['output']}")
    return len(rows)


def extract_atm_density() -> int:
    """Download ATM per 100k adults → atm_density_proxy = min(1.0, raw / 150)."""
    cfg = _INDICATORS["atm"]
    records = _fetch_indicator(cfg["indicator"], cfg["mrv"])
    data = _latest_by_country(records)
    rows = []
    for cc, (v, year) in sorted(data.items()):
        norm = round(min(1.0, v / 150.0), 4)
        rows.append(
            {
                "country_code": cc,
                "atm_density_proxy": norm,
                "raw_atm_per_100k": round(v, 2),
                "data_year": year,
            }
        )
    _write_csv(DATA_DIR / cfg["output"], rows, cfg["fieldnames"])
    logger.info(f"atm_density: {len(rows)} countries → {cfg['output']}")
    return len(rows)


def extract_cash_economy() -> int:
    """Download Findex account ownership % → is_cash_economy = (ownership < 50%)."""
    cfg = _INDICATORS["cash_economy"]
    records = _fetch_indicator(cfg["indicator"], cfg["mrv"])
    data = _latest_by_country(records)
    rows = []
    for cc, (v, year) in sorted(data.items()):
        is_cash = v < 50.0
        rows.append(
            {
                "country_code": cc,
                "percent_account_ownership": round(v, 2),
                "is_cash_economy": is_cash,
                "data_year": year,
            }
        )
    _write_csv(DATA_DIR / cfg["output"], rows, cfg["fieldnames"])
    logger.info(
        f"cash_economy: {len(rows)} countries ({sum(1 for r in rows if r['is_cash_economy'])} cash-dominant) → {cfg['output']}"
    )
    return len(rows)


def extract_all(force: bool = False) -> None:
    """Download all indicators. Skip if output files already exist unless force=True."""
    for name, cfg in _INDICATORS.items():
        out = DATA_DIR / cfg["output"]
        if out.exists() and not force:
            logger.info(f"Skipping {name} — {cfg['output']} already exists (use --force to re-download)")
            continue
        if name == "healthcare":
            extract_healthcare()
        elif name == "road_quality":
            extract_road_quality()
        elif name == "atm":
            extract_atm_density()
        elif name == "cash_economy":
            extract_cash_economy()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    force = "--force" in sys.argv
    extract_all(force=force)
