"""Budget ML scorer.

Loads trained quantile LightGBM models (p10/p50/p90) from model_registry.
Falls back to formula if no trained model is available.

Architecture:
  prediction = baseline_formula + residual_model.predict(features)
  Three quantiles: p10 (optimistic), p50 (median), p90 (pessimistic)
"""

import io
import json
import logging
import math
from typing import Any

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.budget_formula import (
    ACC_TIER_ENCODING,
    estimate_travel_cost,
    formula_baseline,
    haversine,
    seasonal_mult_from_json,
)

logger = logging.getLogger(__name__)

PEOPLE_FACTOR = {1: 1.0, 2: 1.7, 3: 2.3, 4: 2.8}


def _formula_baseline(
    costs: dict[str, Any],
    duration_days: int,
    people_count: int,
    travel_month: int,
    accommodation_tier: str,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
    dest_lat: float = 0.0,
    dest_lng: float = 0.0,
) -> float:
    seasonal = seasonal_mult_from_json(costs.get("seasonal_multiplier"), travel_month)
    avg_daily = float(costs.get("avg_daily_cost_usd") or 80.0)
    travel_cost = estimate_travel_cost(origin_lat, origin_lng, dest_lat, dest_lng, people_count, travel_month)

    def _nullable(key: str) -> float | None:
        v = costs.get(key)
        if v is None:
            return None
        try:
            f = float(v)
            return None if f != f else f
        except (TypeError, ValueError):
            return None

    return formula_baseline(
        avg_daily_cost=avg_daily,
        hostel_usd=_nullable("hostel_usd"),
        budget_usd=_nullable("budget_usd"),
        mid_usd=_nullable("mid_usd"),
        luxury_usd=_nullable("luxury_usd"),
        seasonal_mult=seasonal,
        duration_days=duration_days,
        people_count=people_count,
        accommodation_tier=accommodation_tier,
        travel_to_destination=travel_cost,
    )


def _build_trip_vec(
    duration_days: int,
    people_count: int,
    travel_month: int,
    accommodation_tier: str,
    seasonal: float,
    season_score: float,
    travel_cost: float = 0.0,
    distance_km: float = 0.0,
) -> np.ndarray:
    return np.array(
        [
            float(duration_days),
            math.log1p(float(duration_days)),
            float(people_count),
            float(travel_month) / 12.0,
            float(ACC_TIER_ENCODING.get(accommodation_tier, 2)),
            seasonal,
            season_score,
            travel_cost,
            math.log1p(distance_km),
        ],
        dtype=np.float32,
    )


def _build_dest_vec(
    dest_features: dict[str, Any],
    feature_cols: list[str],
    travel_month: int,
) -> np.ndarray:
    row = []
    for col in feature_cols:
        if col.startswith("act_"):
            val = float(dest_features.get("activities", {}).get(col[4:], 0.0))
        elif col.startswith("season_"):
            val = float(dest_features.get("seasonality", {}).get(int(col[7:]), 0.5))
        elif col == "crowd_index_avg":
            crowd = dest_features.get("crowd_by_month", {})
            val = float(sum(crowd.values()) / len(crowd)) if crowd else 0.5
        elif col == "log_avg_pageviews":
            val = math.log1p(float(dest_features.get("avg_pageviews", 1.0)))
        elif col == "cost_tier":
            daily = float(dest_features.get("avg_daily_cost_usd") or 80.0)
            val = 1.0 if daily < 40 else 2.0 if daily < 80 else 3.0 if daily < 150 else 4.0
        elif col in ("mir_card_accepted", "is_coastal", "has_ski", "has_thermal", "has_mountains", "has_metro"):
            val = 1.0 if dest_features.get(col) else 0.0
        elif col == "script_difficulty":
            val = {"easy": 0.0, "medium": 0.5, "hard": 1.0}.get(
                str(dest_features.get("script_difficulty", "easy")).lower(), 0.0
            )
        elif col == "infrastructure_score":
            hc = float(dest_features.get("healthcare_score", 0.5))
            internet = float(dest_features.get("avg_internet_mbps") or 50.0)
            val = (hc + min(1.0, internet / 200.0)) / 2.0
        else:
            val = float(dest_features.get(col, 0.0))
        row.append(val)
    return np.array(row, dtype=np.float32)


class BudgetScorer:
    """ML budget scorer. Loaded lazily from DB on first use."""

    def __init__(self, model_id: str, blob: bytes | None = None, model_path: str | None = None) -> None:
        self._model_id = model_id
        self._blob = blob
        self._model_path = model_path
        self._artifact: dict | None = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._artifact is not None
        self._loaded = True
        try:
            if self._blob:
                self._artifact = joblib.load(io.BytesIO(self._blob))
                logger.warning("Budget model loaded from DB blob (id=%s) — /tmp was cleared", self._model_id)
            elif self._model_path and __import__("os").path.exists(self._model_path):
                self._artifact = joblib.load(self._model_path)
                logger.warning("Budget model loaded from file %s", self._model_path)
        except Exception as e:
            logger.warning("Failed to load budget model: %s — formula fallback", e)
        return self._artifact is not None

    def predict(
        self,
        costs: dict[str, Any],
        dest_features: dict[str, Any],
        duration_days: int,
        people_count: int,
        travel_month: int,
        accommodation_tier: str,
        origin_lat: float | None = None,
        origin_lng: float | None = None,
    ) -> dict[str, float | str]:
        dest_lat = float(dest_features.get("lat") or 0.0)
        dest_lng = float(dest_features.get("lng") or 0.0)
        travel_cost = estimate_travel_cost(origin_lat, origin_lng, dest_lat, dest_lng, people_count, travel_month)
        distance_km = haversine(origin_lat or 0.0, origin_lng or 0.0, dest_lat, dest_lng) if origin_lat else 0.0

        baseline = _formula_baseline(
            costs,
            duration_days,
            people_count,
            travel_month,
            accommodation_tier,
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
        )

        if not self._ensure_loaded() or self._artifact is None:
            return {
                "total_min": round(baseline * 0.75, 2),
                "total_mid": round(baseline, 2),
                "total_max": round(baseline * 1.35, 2),
                "model_version": "formula-v1",
                "baseline": round(baseline, 2),
                "travel_to_destination": round(travel_cost, 2),
            }

        feature_cols: list[str] = self._artifact["feature_cols"]

        sm = costs.get("seasonal_multiplier") or {}
        if isinstance(sm, str):
            sm = json.loads(sm)
        seasonal = float(sm.get(str(travel_month), 1.0)) if sm else 1.0
        season_score = float(dest_features.get("seasonality", {}).get(travel_month, 0.65))

        trip_vec = _build_trip_vec(
            duration_days,
            people_count,
            travel_month,
            accommodation_tier,
            seasonal,
            season_score,
            travel_cost,
            distance_km,
        )
        dest_vec = _build_dest_vec(dest_features, feature_cols, travel_month)
        X = np.concatenate([trip_vec, dest_vec]).reshape(1, -1).astype(np.float32)

        resid_p10 = float(self._artifact["model_p10"].predict(X)[0])
        resid_p50 = float(self._artifact["model_p50"].predict(X)[0])
        resid_p90 = float(self._artifact["model_p90"].predict(X)[0])

        p10 = max(1.0, baseline + resid_p10)
        p50 = max(1.0, baseline + resid_p50)
        p90 = max(1.0, baseline + resid_p90)

        # Enforce monotonicity
        p10 = min(p10, p50)
        p90 = max(p90, p50)

        return {
            "total_min": round(p10, 2),
            "total_mid": round(p50, 2),
            "total_max": round(p90, 2),
            "model_version": "budget-v1",
            "baseline": round(baseline, 2),
            "travel_to_destination": round(travel_cost, 2),
        }


_scorer_cache: BudgetScorer | None = None


def get_budget_scorer(db: Session) -> BudgetScorer | None:
    """Return active BudgetScorer from registry, or None if not trained yet."""
    global _scorer_cache
    row = db.execute(
        text(
            "SELECT id, model_path, model_blob "
            "FROM model_registry "
            "WHERE model_type = 'budget' AND is_active = true "
            "ORDER BY trained_at DESC LIMIT 1"
        )
    ).fetchone()

    if row is None:
        return None

    model_id = str(row.id)
    if _scorer_cache is not None and _scorer_cache._model_id == model_id:
        return _scorer_cache

    _scorer_cache = BudgetScorer(
        model_id=model_id,
        blob=bytes(row.model_blob) if row.model_blob else None,
        model_path=row.model_path,
    )
    return _scorer_cache
