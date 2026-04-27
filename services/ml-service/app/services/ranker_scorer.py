"""LightGBM LambdaRank scorer.

Implements BaseScorer protocol. Loads trained model from model_registry.model_blob
(persistent — survives container restarts). Falls back to file path, then to
ContentScorer if no model is available.
"""

import io
import logging
import math
import uuid
from typing import Any

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.recommendation import ScoredDestination
from app.services.content_scorer import ContentScorer, _explanation_tags

logger = logging.getLogger(__name__)

_content_scorer = ContentScorer()

ACTIVITY_TYPE_MAP = {
    "beach": "act_beach",
    "culture": "act_culture",
    "adventure": "act_active",
    "active": "act_active",
    "nature": "act_nature",
    "food": "act_food",
    "shopping": "act_shopping",
    "nightlife": "act_nightlife",
    "family": "act_family",
    "romance": "act_romance",
    "wellness": "act_romance",
    "urban": "act_culture",
    "business": "act_business",
}

BUDGET_TIER_RANGES = {
    "budget": (0.0, 0.35),
    "mid": (0.25, 0.60),
    "premium": (0.45, 0.80),
    "luxury": (0.65, 1.0),
}


def _infer_budget_tier(budget_min_usd: float | None, budget_max_usd: float | None) -> str:
    if budget_min_usd is None or budget_max_usd is None:
        return "mid"
    mid = (budget_min_usd + budget_max_usd) / 2.0
    if mid < 800:
        return "budget"
    if mid < 2500:
        return "mid"
    if mid < 6000:
        return "premium"
    return "luxury"


def _build_user_vec(
    profile: dict,
    dest_features: dict[str, Any],
    feature_cols: list[str],
    travel_month: int,
) -> np.ndarray:
    """28-dim user-side features — must match train_ranker._build_pair_features exactly.

    Uses RAW preferences (not pre-computed fits) so LightGBM learns interactions
    from data rather than being given the answer. See train_ranker.py for rationale.
    Dims 25-27 are interaction features added in Phase 7.4b.
    """
    budget_tier = _infer_budget_tier(
        profile.get("budget_min_usd"),
        profile.get("budget_max_usd"),
    )
    b_low, b_high = BUDGET_TIER_RANGES.get(budget_tier, (0.25, 0.60))
    budget_min_norm = float(profile.get("budget_min_usd") or 800) / 20000.0
    budget_max_norm = float(profile.get("budget_max_usd") or 2000) / 20000.0
    cost_index = float(dest_features.get("cost_index", 0.5))
    cost_mid = (b_low + b_high) / 2.0
    budget_fit = 1.0 - max(0.0, min(1.0, abs(cost_index - cost_mid) / 0.5))

    vacation_prefs: list[str] = profile.get("vacation_preferences_ranked") or []
    activities = dest_features.get("activities", {})
    act_match = 0.0
    w_total = 0.0
    for rank, act in enumerate(vacation_prefs[:5], start=1):
        act_name = ACTIVITY_TYPE_MAP.get(act, "").replace("act_", "") or act
        score_val = activities.get(act_name, 0.0)
        w = 6 - rank
        act_match += w * float(score_val)
        w_total += w
    act_match_norm = act_match / w_total if w_total > 0 else 0.0

    top3_beach = float(any(ACTIVITY_TYPE_MAP.get(a) == "act_beach" for a in vacation_prefs[:3]))
    top3_culture = float(any(ACTIVITY_TYPE_MAP.get(a) == "act_culture" for a in vacation_prefs[:3]))
    top3_active = float(any(ACTIVITY_TYPE_MAP.get(a) == "act_active" for a in vacation_prefs[:3]))
    top3_nature = float(any(ACTIVITY_TYPE_MAP.get(a) == "act_nature" for a in vacation_prefs[:3]))

    risk_tolerance = int(profile.get("risk_tolerance") or 3)
    risk_norm = float(risk_tolerance) / 5.0
    is_safety_sensitive = float(risk_tolerance <= 2)

    visa_tolerance = str(profile.get("visa_tolerance") or "any_visa")
    visa_strictness = {"visa_free_only": 1.0, "evisa_ok": 0.5, "any_visa": 0.0}.get(visa_tolerance, 0.0)

    crowd_pref = float(profile.get("crowd_preference") or 3) / 5.0
    n_prefs = float(len(vacation_prefs))

    climate_prefs: list[str] = profile.get("climate_preferences") or ["any"]
    wants_coastal = float(any(p in climate_prefs for p in ("tropical_warm", "mediterranean")))
    wants_mountain = float("cold_snow" in climate_prefs)
    climate_any = float("any" in climate_prefs)

    origin_lat = profile.get("origin_lat")
    origin_lng = profile.get("origin_lng")
    has_origin = float(bool(origin_lat))
    month_norm = float(travel_month) / 12.0
    month_sin = math.sin(2 * math.pi * travel_month / 12)
    month_cos = math.cos(2 * math.pi * travel_month / 12)

    # Budget fit vs actual trip cost
    avg_daily = float(dest_features.get("avg_daily_cost_usd") or 80.0)
    budget_min_usd = float(profile.get("budget_min_usd") or 200)
    budget_max_usd = float(profile.get("budget_max_usd") or 2000)
    typical_duration = str(profile.get("typical_duration") or "standard")
    duration_days = {"weekend": 2, "short": 5, "standard": 10, "long": 21, "extended": 45}.get(typical_duration, 10)
    trip_cost = avg_daily * duration_days
    if budget_min_usd <= trip_cost <= budget_max_usd:
        trip_budget_fit = 1.0
    elif trip_cost < budget_min_usd:
        trip_budget_fit = max(0.3, 1.0 - (budget_min_usd - trip_cost) / max(budget_min_usd, 1) * 0.5)
    else:
        trip_budget_fit = max(0.0, 1.0 - (trip_cost - budget_max_usd) / max(budget_max_usd, 1))

    # Dim 25: crowd_fit — crowd_index vs crowd_preference (interaction)
    crowd_dest = float(dest_features.get("crowd_index_avg", 0.5))
    if not crowd_dest:
        crowd_by_month = dest_features.get("crowd_by_month", {})
        crowd_dest = float(sum(crowd_by_month.values()) / len(crowd_by_month)) if crowd_by_month else 0.5
    crowd_fit = 1.0 - abs(crowd_pref - crowd_dest)

    # Dim 26: climate_match — climate_prefs × dest attributes (interaction)
    is_coastal = 1.0 if dest_features.get("is_coastal") else 0.0
    has_mountains = 1.0 if dest_features.get("has_mountains") else 0.0
    if "any" in climate_prefs:
        climate_match = 0.5
    else:
        hits = sum(
            [
                float(("tropical_warm" in climate_prefs or "mediterranean" in climate_prefs) and is_coastal > 0),
                float("cold_snow" in climate_prefs and has_mountains > 0),
                float("dry_desert" in climate_prefs and float(dest_features.get("safety_score", 0.5)) > 0.4),
            ]
        )
        climate_match = min(1.0, hits * 0.5)

    # Dim 27: origin_proximity — connectivity_score as accessibility proxy
    if origin_lat is not None and origin_lng is not None:
        proximity = float(dest_features.get("connectivity_score", 0.5))
    else:
        proximity = 0.5  # unknown origin → neutral

    return np.array(
        [
            b_low,
            b_high,
            budget_min_norm,
            budget_max_norm,
            cost_mid,
            budget_fit,
            trip_budget_fit,
            float(duration_days) / 45.0,
            act_match_norm,
            top3_beach,
            top3_culture,
            top3_active,
            top3_nature,
            risk_norm,
            is_safety_sensitive,
            visa_strictness,
            crowd_pref,
            wants_coastal,
            wants_mountain,
            has_origin,
            n_prefs,
            month_norm,
            month_sin,
            month_cos,
            climate_any,
            crowd_fit,
            climate_match,
            proximity,
        ],
        dtype=np.float32,
    )


def _build_dest_vec(dest_features: dict[str, Any], feature_cols: list[str]) -> np.ndarray:
    """39-dim destination vector from feature_matrix columns."""
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


class LTRScorer:
    """LightGBM LambdaRank scorer. Loaded lazily from DB blob on first use."""

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
            # 1. Try file first (fast path after warm start)
            if self._model_path:
                import os

                joblib_path = self._model_path.replace(".lgb", ".joblib")
                if os.path.exists(joblib_path):
                    self._artifact = joblib.load(joblib_path)
                    logger.warning("Ranker loaded from file %s", joblib_path)
                    return True
            # 2. Fallback to DB blob (survives container restarts without persistent volume)
            if self._blob:
                self._artifact = joblib.load(io.BytesIO(self._blob))
                logger.warning("Ranker loaded from DB blob (id=%s) — /tmp was cleared", self._model_id)
                return True
            logger.warning("Ranker: no file and no blob — using ContentScorer fallback")
        except Exception as e:
            logger.warning("Ranker load failed: %s — using ContentScorer fallback", e)
        return False

    def score(
        self,
        user_profile: dict,
        destinations: list[dict],
        dest_features: dict[uuid.UUID, dict],
        travel_month: int,
        filters: dict,
    ) -> list[ScoredDestination]:
        if not self._ensure_loaded() or self._artifact is None:
            return _content_scorer.score(user_profile, destinations, dest_features, travel_month, filters)

        model = self._artifact["model"]
        feature_cols: list[str] = self._artifact["feature_cols"]

        visa_tolerance = user_profile.get("visa_tolerance") or "any_visa"
        visa_threshold = {"visa_free_only": 0.80, "evisa_ok": 0.55, "any_visa": 0.0}.get(visa_tolerance, 0.0)
        exclude_ids: set[uuid.UUID] = set(filters.get("exclude_destination_ids", []))
        region_filter: str | None = filters.get("region")

        candidates: list[tuple[dict, dict[str, Any], float]] = []
        X_rows: list[np.ndarray] = []

        for dest in destinations:
            dest_id = uuid.UUID(str(dest["id"]))
            if dest_id in exclude_ids:
                continue
            if region_filter and dest.get("region") != region_filter:
                continue

            f = dest_features.get(dest_id, {})
            visa_score = float(f.get("visa_score", 0.2))
            if visa_score < visa_threshold:
                continue

            user_vec = _build_user_vec(user_profile, f, feature_cols, travel_month)
            dest_vec = _build_dest_vec(f, feature_cols)
            X_rows.append(np.concatenate([user_vec, dest_vec]))
            candidates.append((dest, f, visa_score))

        if not candidates:
            return []

        X = np.stack(X_rows, dtype=np.float32)
        raw_scores = model.predict(X)

        # Sigmoid normalisation: score-independent, stable across different request sizes.
        # Per-batch min-max caused the top result to always show 100% regardless of quality.
        scores_norm = 1.0 / (1.0 + np.exp(-raw_scores.astype(np.float64)))

        # Pre-compute content breakdowns for all candidates (used as explanation layer).
        # LTR determines ranking order; content breakdown provides human-readable explanation.
        # This mirrors production systems (YouTube, TikTok) that rank with one model and
        # explain with another.
        content_results: dict[uuid.UUID, ScoredDestination] = {}
        dest_subset = [d for d, _, _ in candidates]
        feat_subset = {uuid.UUID(str(d["id"])): f for d, f, _ in candidates}
        for cr in _content_scorer.score(user_profile, dest_subset, feat_subset, travel_month, filters):
            content_results[cr.destination_id] = cr

        results: list[ScoredDestination] = []
        for i, (dest, f, visa_score) in enumerate(candidates):
            dest_id = uuid.UUID(str(dest["id"]))
            score = float(scores_norm[i])
            safety = float(f.get("safety_score", 0.5))
            season = float(f.get("seasonality", {}).get(travel_month, 0.5))
            avg_daily = f.get("avg_daily_cost_usd")

            # Merge: content breakdown (9 factors) + LTR raw scores for auditability
            content_bd = content_results[dest_id].score_breakdown if dest_id in content_results else {}
            breakdown = {
                **content_bd,
                "ltr_score_raw": round(float(raw_scores[i]), 4),
                "ltr_score": round(score, 4),
            }
            tags = _explanation_tags(breakdown, f, visa_score, safety)

            results.append(
                ScoredDestination(
                    destination_id=dest_id,
                    name=dest["name"],
                    country_code=dest["country_code"],
                    region=dest.get("region", ""),
                    score=round(score, 4),
                    score_breakdown=breakdown,
                    explanation_tags=tags,
                    avg_daily_cost_usd=float(avg_daily) if avg_daily else None,
                    season_score=round(season, 4),
                    safety_score=round(safety, 4),
                )
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results


def get_active_scorer(db: Session) -> LTRScorer | ContentScorer:
    """Return active LTRScorer if trained model exists in registry, else ContentScorer."""
    row = db.execute(
        text(
            "SELECT id, model_path, model_blob "
            "FROM model_registry "
            "WHERE model_type = 'lambdarank' AND is_active = true "
            "ORDER BY trained_at DESC LIMIT 1"
        )
    ).fetchone()

    if row:
        return LTRScorer(
            model_id=str(row.id),
            blob=bytes(row.model_blob) if row.model_blob else None,
            model_path=row.model_path,
        )

    return _content_scorer
