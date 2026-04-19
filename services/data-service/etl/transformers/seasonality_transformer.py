"""Transform Open-Meteo weather data into seasonality records with season_score.

season_score formula (3 components):
  temp_comfort    — ideal 18–26°C, linear decay outside (range 20°C)
  precip_comfort  — absolute scale: 0mm=0 penalty, 200mm/month=full penalty
                    (NOT relative to destination max — that killed tropical contrast)
  humidity_comfort — ideal ≤70% RH, linear penalty above 70% up to 100%

Weights: 0.50 temp + 0.30 precip + 0.20 humidity

Why absolute precipitation scale:
  Per-destination normalization (old code) made Bangkok Dec (7mm) score 0 penalty
  and Bangkok Sep (300mm) score full penalty — relatively correct within Bangkok,
  but globally incomparable. With absolute scale both are correctly scored vs global
  benchmark of 200mm/month being "very rainy".

Why humidity:
  30°C + 90% RH (Bangkok Sep) ≠ 30°C + 40% RH (Cairo summer).
  Open-Meteo provides relative_humidity_2m_mean at no cost.
"""

import logging
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)

IDEAL_TEMP_MIN = 18.0
IDEAL_TEMP_MAX = 26.0
TEMP_DECAY_RANGE = 20.0  # degrees from ideal edge → score 0

PRECIP_FULL_PENALTY_MM = 200.0  # mm/month = maximum rain penalty (tropical monsoon)

HUMIDITY_OK_THRESHOLD = 70.0  # % RH below this = no penalty
HUMIDITY_DECAY_RANGE = 30.0  # % RH above threshold → score 0 at 100%


def _temp_comfort(temp_c: float) -> float:
    """1.0 in [18, 26]°C, linear decay outside. 0°C → 0.10, 36°C → 0.50, -2°C → 0.0."""
    if IDEAL_TEMP_MIN <= temp_c <= IDEAL_TEMP_MAX:
        return 1.0
    distance = min(abs(temp_c - IDEAL_TEMP_MIN), abs(temp_c - IDEAL_TEMP_MAX))
    return max(0.0, 1.0 - distance / TEMP_DECAY_RANGE)


def _precip_comfort(avg_mm: float) -> float:
    """1.0 at 0mm, 0.0 at 200mm+. Absolute scale — comparable across all destinations."""
    return max(0.0, 1.0 - avg_mm / PRECIP_FULL_PENALTY_MM)


def _humidity_comfort(rh_pct: float) -> float:
    """1.0 at ≤70% RH, linear decay above. 90% RH → 0.33, 100% RH → 0.0."""
    return max(
        0.0, 1.0 - max(0.0, rh_pct - HUMIDITY_OK_THRESHOLD) / HUMIDITY_DECAY_RANGE
    )


def transform_seasonality(raw: list[dict]) -> list[dict]:
    """Aggregate daily weather data → monthly averages + season_score per destination."""
    records = []

    for item in raw:
        destination_id = item["destination_id"]
        daily = item["weather"].get("daily", {})

        dates = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        precips = daily.get("precipitation_sum", [])
        humidities = daily.get("relative_humidity_2m_mean", [])

        if not dates:
            continue

        monthly: dict[int, dict[str, list]] = defaultdict(
            lambda: {"temps": [], "precips": [], "humidities": []}
        )
        for i, date_str in enumerate(dates):
            month = int(date_str[5:7])
            if i < len(temps) and temps[i] is not None:
                monthly[month]["temps"].append(temps[i])
            if i < len(precips) and precips[i] is not None:
                monthly[month]["precips"].append(precips[i])
            if i < len(humidities) and humidities[i] is not None:
                monthly[month]["humidities"].append(humidities[i])

        for month, data in monthly.items():
            if not data["temps"]:
                continue

            avg_temp = float(np.mean(data["temps"]))
            # monthly total (sum of daily values), not mean — needed for absolute scale
            avg_precip = float(np.sum(data["precips"])) if data["precips"] else 0.0
            avg_humidity = (
                float(np.mean(data["humidities"])) if data["humidities"] else None
            )

            tc = _temp_comfort(avg_temp)
            pc = _precip_comfort(avg_precip)
            hc = _humidity_comfort(avg_humidity) if avg_humidity is not None else 1.0

            season_score = round(0.50 * tc + 0.30 * pc + 0.20 * hc, 4)

            records.append(
                {
                    "destination_id": destination_id,
                    "month": month,
                    "avg_temp_c": round(avg_temp, 2),
                    "avg_precipitation_mm": round(avg_precip, 2),
                    "avg_humidity_pct": round(avg_humidity, 1)
                    if avg_humidity is not None
                    else None,
                    "season_score": season_score,
                }
            )

    logger.info(f"Transformed {len(records)} seasonality records.")
    return records
