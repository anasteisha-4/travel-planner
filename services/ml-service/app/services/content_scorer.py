"""Content-based scorer for destination recommendations.

Accepts a full UserProfile (12 onboarding fields) and returns ranked
ScoredDestination list with score_breakdown and explanation_tags.

Scoring factors and weights:
  activity_match   0.28  — ranked vacation_preferences vs activity scores
  budget_fit       0.18  — band matching budget vs cost_index
  season           0.18  — season_score for travel_month
  visa             0.12  — hard-filtered + soft score
  safety           0.10  — safety_score vs risk_tolerance
  language         0.06  — ru/en speaking score vs language_comfort
  crowd            0.04  — crowd_preference vs crowd_index
  climate          0.04  — attribute match vs climate_preferences
"""

import uuid
from typing import Any, Protocol, runtime_checkable

from app.schemas.recommendation import ScoredDestination


@runtime_checkable
class BaseScorer(Protocol):
    def score(
        self,
        user_profile: dict,
        destinations: list[dict],
        dest_features: dict[uuid.UUID, dict],
        travel_month: int,
        filters: dict,
    ) -> list[ScoredDestination]: ...


ACTIVITY_WEIGHT_BY_RANK = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}

# risk_tolerance 1-5 → minimum safety_score required
RISK_SAFETY_THRESHOLD = {1: 0.70, 2: 0.55, 3: 0.40, 4: 0.20, 5: 0.0}

# visa_tolerance → minimum visa_score to include
VISA_FILTER = {
    "visa_free_only": 0.80,
    "evisa_ok": 0.55,
    "any_visa": 0.0,
}

# typical_duration → days
DURATION_DAYS = {
    "weekend": 2,
    "short": 5,
    "standard": 10,
    "long": 21,
    "extended": 45,
}

# climate pref keywords → destination attribute flags
CLIMATE_ATTRIBUTE_MAP: dict[str, list[str]] = {
    "tropical_warm": ["is_coastal"],
    "mediterranean": ["is_coastal"],
    "continental_mild": [],
    "cold_snow": ["has_ski"],
    "dry_desert": [],
    "any": [],
}


def _percentile_rank(value: float, all_values: list[float]) -> float:
    if not all_values:
        return 0.5
    return sum(1 for v in all_values if v < value) / len(all_values)


def _activity_match_score(
    vacation_prefs_ranked: list[str],
    activities: dict[str, float],
    all_activity_avgs: list[float],
) -> float:
    """Weighted match: rank-1 pref gets weight 5, rank-5 gets weight 1.
    Raw score = sum(weight * activity_score) / max_possible.
    Then percentile-ranked globally to stretch the range.
    """
    if not vacation_prefs_ranked or not activities:
        return 0.5

    total_weight = 0.0
    weighted_sum = 0.0
    for i, pref in enumerate(vacation_prefs_ranked[:5]):
        weight = ACTIVITY_WEIGHT_BY_RANK.get(i + 1, 1)
        score = activities.get(pref, 0.0)
        weighted_sum += weight * score
        total_weight += weight

    raw = weighted_sum / total_weight if total_weight > 0 else 0.0
    return _percentile_rank(raw, all_activity_avgs) if all_activity_avgs else raw


def _budget_fit_score(
    budget_min_usd: float | None,
    budget_max_usd: float | None,
    cost_index: float,
    avg_daily_cost_usd: float | None,
    typical_duration: str | None,
) -> float:
    """Band matching: check if avg_daily_cost_usd × duration fits within budget range.
    Falls back to cost_index distance if budget not set.
    """
    if budget_min_usd is None or budget_max_usd is None:
        return 1.0 - abs(cost_index - 0.5)

    duration_days = DURATION_DAYS.get(typical_duration or "standard", 10)
    daily_cost = avg_daily_cost_usd or (cost_index * 300)
    trip_cost = daily_cost * duration_days

    budget_mid = (budget_min_usd + budget_max_usd) / 2.0
    budget_range = max(budget_max_usd - budget_min_usd, budget_mid * 0.2)

    if budget_min_usd <= trip_cost <= budget_max_usd:
        return 1.0
    overshoot = budget_min_usd - trip_cost if trip_cost < budget_min_usd else trip_cost - budget_max_usd

    return max(0.0, 1.0 - overshoot / (budget_range * 2))


def _safety_score(safety: float, risk_tolerance: int | None) -> float:
    """Returns 1.0 for destinations above threshold, 0 below, continuous near boundary."""
    threshold = RISK_SAFETY_THRESHOLD.get(risk_tolerance or 3, 0.40)
    if safety >= threshold:
        # Reward higher safety, but don't over-penalise lower within tolerance
        return 0.5 + 0.5 * min(safety, 1.0)
    # Below threshold: linear decay
    return max(0.0, safety / threshold * 0.5)


def _language_score(
    features: dict[str, Any],
    language_comfort: list[str],
) -> float:
    ru = float(features.get("russian_speaking_score", 0.0))
    en = float(features.get("english_speaking_score", 0.0))
    script = float(features.get("script_difficulty", 0.5))

    if not language_comfort or "any" in language_comfort:
        return 0.5 + 0.5 * (1 - script * 0.3)

    score = 0.0
    if "ru" in language_comfort:
        score = max(score, ru)
    if "en" in language_comfort:
        score = max(score, en)
    # script penalty applied softly
    return min(1.0, score * (1 - script * 0.2))


def _crowd_score(crowd_index: float, crowd_preference: int | None) -> float:
    """crowd_preference: 1=wants quiet, 5=wants lively."""
    pref = (crowd_preference or 3) / 5.0
    return 1.0 - abs(pref - crowd_index)


def _climate_match(features: dict[str, Any], climate_prefs: list[str]) -> float:
    if not climate_prefs or "any" in climate_prefs:
        return 0.7

    hits = 0
    total = 0
    for pref in climate_prefs:
        required_attrs = CLIMATE_ATTRIBUTE_MAP.get(pref, [])
        if not required_attrs:
            hits += 1
            total += 1
            continue
        total += 1
        if any(features.get(attr, False) for attr in required_attrs):
            hits += 1

    return hits / total if total > 0 else 0.5


def _region_boost(
    dest_region: str | None,
    dest_subregion: str | None,
    liked_dest_features: list[dict],
) -> float:
    """Small boost (up to 0.15) for destinations in same region/subregion as liked ones."""
    if not liked_dest_features:
        return 0.0
    same_subregion = sum(1 for f in liked_dest_features if f.get("subregion") == dest_subregion and dest_subregion)
    same_region = sum(1 for f in liked_dest_features if f.get("region") == dest_region and dest_region)
    return min(0.15, same_subregion * 0.08 + same_region * 0.04)


def _connectivity_boost(connectivity_score: float, origin_lat: float | None) -> float:
    """Weight connectivity by whether user has a known origin (lat set)."""
    if origin_lat is None:
        return connectivity_score * 0.6
    return connectivity_score


def _explanation_tags(
    breakdown: dict[str, float],
    features: dict[str, Any],
    visa_score: float,
    safety_score: float,
) -> list[str]:
    tags = []
    if visa_score >= 0.80:
        tags.append("visa_free")
    elif visa_score >= 0.55:
        tags.append("easy_visa")
    if features.get("is_coastal"):
        tags.append("beach")
    if features.get("has_ski"):
        tags.append("skiing")
    if features.get("has_thermal"):
        tags.append("hot_springs")
    if features.get("has_mountains"):
        tags.append("mountains")
    if safety_score >= 0.75:
        tags.append("safe")
    cost_usd = features.get("avg_daily_cost_usd")
    if cost_usd is not None:
        if cost_usd < 60:
            tags.append("affordable")
        elif cost_usd > 200:
            tags.append("premium")
    if breakdown.get("season", 0) >= 0.75:
        tags.append("perfect_season")
    if breakdown.get("activity_match", 0) >= 0.75:
        tags.append("great_match")
    return tags[:5]


class ContentScorer:
    def score(
        self,
        user_profile: dict,
        destinations: list[dict],
        dest_features: dict[uuid.UUID, dict],
        travel_month: int,
        filters: dict,
    ) -> list[ScoredDestination]:
        vacation_prefs: list[str] = user_profile.get("vacation_preferences_ranked") or []
        budget_min_usd: float | None = user_profile.get("budget_min_usd")
        budget_max_usd: float | None = user_profile.get("budget_max_usd")
        typical_duration: str | None = user_profile.get("typical_duration")
        risk_tolerance: int | None = user_profile.get("risk_tolerance")
        visa_tolerance: str = user_profile.get("visa_tolerance") or "any_visa"
        language_comfort: list[str] = user_profile.get("language_comfort") or ["any"]
        crowd_preference: int | None = user_profile.get("crowd_preference")
        climate_prefs: list[str] = user_profile.get("climate_preferences") or []
        liked_dest_ids: list[int] = user_profile.get("liked_destination_ids") or []
        origin_lat: float | None = user_profile.get("origin_lat")

        # Citizenship is handled at the data-loading layer — visa_score in dest_features
        # already reflects the correct citizenship passed to get_destination_features().
        exclude_ids: set[uuid.UUID] = set(filters.get("exclude_destination_ids", []))
        region_filter: str | None = filters.get("region")

        visa_threshold = VISA_FILTER.get(visa_tolerance, 0.0)

        # Pre-compute liked destination metadata for region boost
        liked_features = [
            {
                "region": dest_features.get(uuid.UUID(str(d)), {}).get("region"),
                "subregion": dest_features.get(uuid.UUID(str(d)), {}).get("subregion"),
            }
            for d in liked_dest_ids
        ]

        # Build global distribution of weighted activity averages for percentile ranking
        all_activity_avgs: list[float] = []
        if vacation_prefs:
            for dest in destinations:
                dest_id = uuid.UUID(str(dest["id"]))
                f = dest_features.get(dest_id, {})
                activities: dict[str, float] = f.get("activities", {})
                if activities:
                    total_w = 0.0
                    total_s = 0.0
                    for i, pref in enumerate(vacation_prefs[:5]):
                        w = ACTIVITY_WEIGHT_BY_RANK.get(i + 1, 1)
                        total_s += w * activities.get(pref, 0.0)
                        total_w += w
                    if total_w > 0:
                        all_activity_avgs.append(total_s / total_w)

        results: list[ScoredDestination] = []

        for dest in destinations:
            dest_id = uuid.UUID(str(dest["id"]))

            if dest_id in exclude_ids:
                continue
            if region_filter and dest.get("region") != region_filter:
                continue

            f = dest_features.get(dest_id, {})

            # --- Per-factor scores ---
            visa_score = float(f.get("visa_score", 0.2))
            if visa_score < visa_threshold:
                continue  # hard filter

            safety = float(f.get("safety_score", 0.5))
            season = f.get("seasonality", {}).get(travel_month, 0.5)
            cost_index = float(f.get("cost_index", 0.5))
            avg_daily_cost_usd = f.get("avg_daily_cost_usd")
            crowd_index = f.get("crowd_by_month", {}).get(travel_month, 0.5)
            connectivity = float(f.get("connectivity_score", 0.0))
            activities: dict[str, float] = f.get("activities", {})

            act_score = _activity_match_score(vacation_prefs, activities, all_activity_avgs)
            budget_score = _budget_fit_score(
                budget_min_usd, budget_max_usd, cost_index, avg_daily_cost_usd, typical_duration
            )
            safety_sc = _safety_score(safety, risk_tolerance)
            lang_sc = _language_score(f, language_comfort)
            crowd_sc = _crowd_score(crowd_index, crowd_preference)
            climate_sc = _climate_match(f, climate_prefs)
            conn_sc = _connectivity_boost(connectivity, origin_lat)
            region_boost = _region_boost(dest.get("region"), dest.get("subregion"), liked_features)

            breakdown = {
                "activity_match": round(act_score, 4),
                "budget_fit": round(budget_score, 4),
                "season": round(float(season), 4),
                "visa": round(visa_score, 4),
                "safety": round(safety_sc, 4),
                "language": round(lang_sc, 4),
                "crowd": round(crowd_sc, 4),
                "climate": round(climate_sc, 4),
                "connectivity": round(conn_sc, 4),
                "region_boost": round(region_boost, 4),
            }

            composite = (
                0.28 * act_score
                + 0.18 * budget_score
                + 0.18 * float(season)
                + 0.12 * visa_score
                + 0.10 * safety_sc
                + 0.06 * lang_sc
                + 0.04 * crowd_sc
                + 0.04 * climate_sc
            )
            # Connectivity and region boost are additive on top (capped at 1.0)
            composite = min(1.0, composite + 0.04 * conn_sc + region_boost * 0.05)

            tags = _explanation_tags(breakdown, f, visa_score, safety)

            results.append(
                ScoredDestination(
                    destination_id=dest_id,
                    name=dest["name"],
                    country_code=dest["country_code"],
                    region=dest.get("region", ""),
                    score=round(composite, 4),
                    score_breakdown=breakdown,
                    explanation_tags=tags,
                    avg_daily_cost_usd=float(avg_daily_cost_usd) if avg_daily_cost_usd else None,
                    season_score=round(float(season), 4),
                    safety_score=round(safety, 4),
                )
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results
