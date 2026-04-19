"""Extract Henley Passport Index visa data from CSV."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def extract_henley() -> pd.DataFrame:
    """Load Henley Passport Index matrix.

    Expected format: rows = citizenship ISO2, columns = destination ISO2,
    values = VF (visa free) / VOA (visa on arrival) / VR (visa required) / NA (no admission)
    """
    path = DATA_DIR / "henley_passport_index.csv"
    if not path.exists():
        raise FileNotFoundError(f"Henley CSV not found: {path}")
    df = pd.read_csv(path, index_col=0)
    logger.info(
        f"Loaded Henley index: {df.shape[0]} citizenships × {df.shape[1]} destinations"
    )
    return df
