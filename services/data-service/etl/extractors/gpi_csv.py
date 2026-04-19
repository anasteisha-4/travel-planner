"""Extract Global Peace Index data from CSV."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def extract_gpi() -> pd.DataFrame:
    """Load GPI scores from CSV.

    Expected columns: country_iso2, gpi_score, gpi_rank, year
    """
    path = DATA_DIR / "gpi_scores.csv"
    if not path.exists():
        raise FileNotFoundError(f"GPI CSV not found: {path}")
    # keep_default_na=False prevents pandas from converting "NA" (Namibia ISO2) to NaN
    df = pd.read_csv(path, keep_default_na=False)
    logger.info(f"Loaded {len(df)} GPI records from {path}")
    return df
