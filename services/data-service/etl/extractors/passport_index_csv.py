"""Extract ilyankou/passport-index-dataset (tidy ISO2 format).

Source: https://github.com/ilyankou/passport-index-dataset (MIT License)
Updated: January 2025. Covers 199×199 passport/destination pairs.

Values: visa free, numeric days (visa-free stay), visa on arrival,
        e-visa, eta, visa required, no admission, -1 (self-travel)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def extract_passport_index() -> pd.DataFrame:
    """Load passport index in tidy 3-column format (Passport, Destination, Requirement).

    Returns DataFrame with columns: passport_code, destination_code, requirement
    """
    path = DATA_DIR / "passport_index.csv"
    if not path.exists():
        raise FileNotFoundError(f"Passport index CSV not found: {path}")

    df = pd.read_csv(path, keep_default_na=False)
    df.columns = ["passport_code", "destination_code", "requirement"]
    logger.info(f"Loaded Passport Index: {len(df)} rows")
    return df
