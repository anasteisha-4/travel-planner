"""Content-based scorer for destination recommendations.

Accepts a full UserProfile (12 onboarding fields) and returns ranked
ScoredDestination list with score_breakdown and explanation_tags.

Hard filters (applied before composite, disqualify destination entirely):
  visa_tolerance      — minimum visa_score threshold (VISA_FILTER)
  risk_tolerance      — minimum safety_score threshold (RISK_SAFETY_THRESHOLD)

Soft factors (weighted composite, sum = 1.0 when all signals present):
  activity_match        0.22  — rank-weighted vacation_preferences vs activity scores
  liked_dest_similarity 0.15  — cosine similarity to mean activity vector of liked dests
  budget_fit            0.13  — band matching budget vs cost_index
  origin_proximity      0.10  — haversine distance decay from origin city
  season_fit            0.10  — season_score for travel_month
  safety_modulation     0.08  — safety_score vs risk_tolerance (above threshold = modulation)
  language_match        0.07  — ru/en speaking score vs language_comfort
  visa_effort           0.05  — soft visa score (after hard filter)
  climate_match         0.05  — attribute match vs climate_preferences
  crowd_fit             0.05  — crowd_preference vs crowd_index

Optional signals (liked_similarity, origin_proximity): when absent (None),
their weight is redistributed proportionally across remaining factors via
dynamic weight normalisation (divide by total_weight of present factors).

Soft penalties (additive, applied after composite):
  language_hard_penalty   -0.25  when dest non-ru-friendly and user ru-only
  liked_dest_visited       -0.10  when dest is in liked_destination_ids (already known)
"""

import uuid
from typing import Any, Protocol, runtime_checkable

import numpy as np

from app.schemas.recommendation import ScoredDestination
from app.services.travelpayouts_service import FareEstimate, get_cached_fare_only_usd


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

# Base weights when all signals present (sum = 1.0)
COMPOSITE_WEIGHTS: dict[str, float] = {
    "activity_match": 0.22,
    "liked_dest_similarity": 0.15,
    "budget_fit": 0.13,
    "origin_proximity": 0.10,
    "season_fit": 0.10,
    "safety_modulation": 0.08,
    "language_match": 0.07,
    "visa_effort": 0.05,
    "climate_match": 0.05,
    "crowd_fit": 0.05,
}

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


ACTIVITY_TYPES = [
    "beach",
    "culture",
    "nature",
    "adventure",
    "food",
    "nightlife",
    "wellness",
    "shopping",
    "family",
    "urban",
]


def _activity_vector(activities: dict[str, float]) -> np.ndarray:
    return np.array([activities.get(a, 0.0) for a in ACTIVITY_TYPES], dtype=np.float64)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _liked_destinations_similarity(
    liked_dest_ids: list,
    dest_id: uuid.UUID,
    dest_region: str | None,
    dest_subregion: str | None,
    dest_activities: dict[str, float],
    dest_lookup: dict[str, dict],
) -> float | None:
    """Cosine similarity between dest and mean activity vector of liked destinations.

    Returns None when no liked destinations are found in the lookup
    (signal absent — do not penalise).
    """
    if not liked_dest_ids:
        return None

    liked_vecs: list[np.ndarray] = []
    liked_regions: list[str | None] = []
    liked_subregions: list[str | None] = []

    for lid in liked_dest_ids:
        key = str(lid)
        if key == str(dest_id):
            continue
        entry = dest_lookup.get(key)
        if entry is None:
            continue
        liked_vecs.append(_activity_vector(entry.get("activities", {})))
        liked_regions.append(entry.get("region"))
        liked_subregions.append(entry.get("subregion"))

    if not liked_vecs:
        return None

    mean_vec = np.mean(liked_vecs, axis=0)
    dest_vec = _activity_vector(dest_activities)
    sim_activity = _cosine_similarity(mean_vec, dest_vec)

    same_subregion = dest_subregion and any(s == dest_subregion for s in liked_subregions)
    same_region = dest_region and any(r == dest_region for r in liked_regions)

    score = 0.6 * sim_activity
    if same_subregion:
        score += 0.3
    elif same_region:
        score += 0.15

    return min(1.0, score)


def _activity_match_score(
    vacation_prefs_ranked: list[str],
    activities: dict[str, float],
) -> float:
    """Weighted match: rank-1 pref gets weight 5, rank-5 gets weight 1.
    Raw score = sum(weight * activity_score) / total_weight.

    Percentile ranking was removed: when all destinations score similarly
    (e.g. 0.74–0.81 range), percentile collapses small real differences into
    arbitrary discrete jumps (0.0 vs 0.33 vs 0.67), causing the lowest raw
    scorer to receive 0.0 even when it is a strong match.
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

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _budget_fit_score(
    budget_min_usd: float | None,
    budget_max_usd: float | None,
    cost_index: float,
    avg_daily_cost_usd: float | None,
    typical_duration_days: int,
    route_cost_usd: float | None = None,
) -> float:
    """Band matching: check if avg_daily_cost_usd × duration + route fare fits within budget range.
    Falls back to cost_index distance if budget not set.
    """
    if budget_min_usd is None or budget_max_usd is None:
        return 1.0 - abs(cost_index - 0.5)

    duration_days = typical_duration_days
    daily_cost = avg_daily_cost_usd or (cost_index * 300)
    trip_cost = daily_cost * duration_days + (route_cost_usd or 0.0)

    budget_mid = (budget_min_usd + budget_max_usd) / 2.0
    budget_range = max(budget_max_usd - budget_min_usd, budget_mid * 0.2)

    if budget_min_usd <= trip_cost <= budget_max_usd:
        return 1.0
    overshoot = budget_min_usd - trip_cost if trip_cost < budget_min_usd else trip_cost - budget_max_usd

    return max(0.0, 1.0 - overshoot / (budget_range * 2))


def _avg_daily_budget_usd(
    avg_daily_cost_usd: float | None,
    cost_index: float,
    duration_days: int,
    route_cost_usd: float | None = None,
) -> float:
    daily_cost = avg_daily_cost_usd or (cost_index * 300)
    return (daily_cost * duration_days + (route_cost_usd or 0.0)) / max(duration_days, 1)


def resolve_accommodation_tier(
    rest_level: str | None,
    budget_max_usd: float | None,
    fallback: str = "mid",
) -> str:
    tier_by_rest_level = {
        "economy": "budget",
        "standard": "mid",
        "comfort": "mid",
        "luxury": "luxury",
    }
    tier = tier_by_rest_level.get(rest_level or "", fallback)

    if budget_max_usd is None:
        return tier
    if budget_max_usd < 900:
        return "budget"
    if budget_max_usd < 3000 and tier == "luxury":
        return "mid"
    return tier


def _cached_route_fare(
    user_profile: dict,
    destination: dict,
    features: dict[str, Any],
    travel_month: int,
    duration_days: int,
) -> FareEstimate | None:
    return get_cached_fare_only_usd(
        origin_city_name=user_profile.get("origin_city_name"),
        origin_lat=user_profile.get("origin_lat"),
        origin_lng=user_profile.get("origin_lng"),
        destination_name=destination.get("name"),
        destination_lat=destination.get("lat") or features.get("lat"),
        destination_lng=destination.get("lng") or features.get("lng"),
        destination_country_code=destination.get("country_code"),
        travel_month=travel_month,
        duration_days=duration_days,
        accommodation_tier=resolve_accommodation_tier(
            user_profile.get("rest_level"),
            user_profile.get("budget_max_usd"),
        ),
    )


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


def _language_penalty(features: dict[str, Any], language_comfort: list[str]) -> float:
    """Hard-ish penalty (-0.25) when destination language doesn't match user comfort.

    Only applies when comfort is explicit (not ["any"] or empty).
    ru-only: penalise if russian_speaking_score < 0.3.
    ru+en:   penalise only if BOTH ru < 0.3 AND en < 0.3.
    """
    if not language_comfort or "any" in language_comfort:
        return 0.0

    ru = float(features.get("russian_speaking_score", 0.0))
    en = float(features.get("english_speaking_score", 0.0))

    wants_ru = "ru" in language_comfort
    wants_en = "en" in language_comfort

    if wants_ru and not wants_en:
        return -0.25 if ru < 0.3 else 0.0

    if wants_ru and wants_en:
        return -0.25 if ru < 0.3 and en < 0.3 else 0.0

    # en-only: penalise if english_speaking_score < 0.3
    return -0.25 if en < 0.3 else 0.0


def _liked_visited_penalty(dest_id: uuid.UUID, liked_dest_ids: list) -> float:
    """Return -0.10 if this destination is already in the user's liked list.

    We want to recommend new destinations, not repeat what the user already knows.
    """
    if not liked_dest_ids:
        return 0.0
    return -0.10 if any(str(lid) == str(dest_id) for lid in liked_dest_ids) else 0.0


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
    """Kept for backward compatibility — superseded by _liked_destinations_similarity."""
    if not liked_dest_features:
        return 0.0
    same_subregion = sum(1 for f in liked_dest_features if f.get("subregion") == dest_subregion and dest_subregion)
    same_region = sum(1 for f in liked_dest_features if f.get("region") == dest_region and dest_region)
    return min(0.15, same_subregion * 0.08 + same_region * 0.04)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _origin_proximity_score(
    origin_lat: float | None,
    origin_lng: float | None,
    dest_lat: float | None,
    dest_lng: float | None,
) -> float | None:
    """Distance-based score with smooth decay. Returns None when origin is unknown."""
    if origin_lat is None or origin_lng is None or dest_lat is None or dest_lng is None:
        return None
    d = _haversine_km(origin_lat, origin_lng, float(dest_lat), float(dest_lng))
    if d < 500:
        return 1.00
    elif d < 1500:
        return 0.90
    elif d < 3000:
        return 0.75
    elif d < 5000:
        return 0.60
    elif d < 8000:
        return 0.45
    elif d < 12000:
        return 0.30
    else:
        return 0.20


def _explanation_tags(
    breakdown: dict[str, float],
    features: dict[str, Any],
    visa_score: float,
    safety_score: float,
    travel_month: int | None = None,
) -> list[str]:
    tags = []
    if visa_score >= 0.80:
        tags.append("visa_free")
    elif visa_score >= 0.55:
        tags.append("easy_visa")
    if _is_beach_label_active(features, travel_month):
        tags.append("beach")
    if _is_ski_label_active(features, travel_month):
        tags.append("skiing")
    if _is_hot_springs_label_active(features):
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
    if breakdown.get("season_fit", 0) >= 0.75:
        tags.append("perfect_season")
    if breakdown.get("activity_match", 0) >= 0.75:
        tags.append("great_match")
    return tags[:5]


def _is_beach_label_active(features: dict[str, Any], travel_month: int | None) -> bool:
    if not features.get("is_coastal"):
        return False
    beach_score = float((features.get("activities") or {}).get("beach", 0.0))
    if beach_score < 0.65:
        return False
    if travel_month is None:
        return False
    season_score = float((features.get("seasonality") or {}).get(travel_month, 0.0))
    weather = (features.get("season_weather") or {}).get(travel_month) or {}
    avg_temp = weather.get("avg_temp_c")
    if avg_temp is None:
        return season_score >= 0.75
    min_temp = 22.0 if _is_cool_coast(features) else 18.0
    return season_score >= 0.60 and float(avg_temp) >= min_temp


def _is_cool_coast(features: dict[str, Any]) -> bool:
    lat = features.get("lat")
    if lat is None:
        return False
    return abs(float(lat)) >= 50.0


def _is_ski_label_active(features: dict[str, Any], travel_month: int | None) -> bool:
    if not features.get("has_ski"):
        return False
    if not features.get("has_mountains"):
        return False
    if travel_month is None:
        return False
    lat = features.get("lat")
    northern = lat is None or float(lat) >= 0
    ski_months = {12, 1, 2, 3} if northern else {6, 7, 8, 9}
    return travel_month in ski_months


def _is_hot_springs_label_active(features: dict[str, Any]) -> bool:
    if not features.get("has_thermal"):
        return False
    if features.get("has_mountains"):
        return True
    altitude = features.get("altitude_m")
    if altitude is not None and float(altitude) >= 100.0:
        return True
    return not features.get("is_coastal")


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
        typical_duration_days: int = int(user_profile.get("typical_duration_days") or 10)
        risk_tolerance: int | None = user_profile.get("risk_tolerance")
        visa_tolerance: str = user_profile.get("visa_tolerance") or "any_visa"
        language_comfort: list[str] = user_profile.get("language_comfort") or ["any"]
        crowd_preference: int | None = user_profile.get("crowd_preference")
        climate_prefs: list[str] = user_profile.get("climate_preferences") or []
        liked_dest_ids: list = user_profile.get("liked_destination_ids") or []
        origin_lat: float | None = user_profile.get("origin_lat")
        origin_lng: float | None = user_profile.get("origin_lng")

        # Citizenship is handled at the data-loading layer — visa_score in dest_features
        # already reflects the correct citizenship passed to get_destination_features().
        exclude_ids: set[uuid.UUID] = set(filters.get("exclude_destination_ids", []))
        region_filter: str | None = filters.get("region")
        include_route_fares = bool(filters.get("include_route_fares", True))

        visa_threshold = VISA_FILTER.get(visa_tolerance, 0.0)

        # Build lookup: dest_id_str → {region, subregion, activities} for liked similarity
        dest_lookup: dict[str, dict] = {}
        for dest in destinations:
            dest_id_str = str(dest["id"])
            f = dest_features.get(uuid.UUID(dest_id_str), {})
            dest_lookup[dest_id_str] = {
                "region": dest.get("region"),
                "subregion": dest.get("subregion"),
                "activities": f.get("activities", {}),
            }

        has_liked_signal = bool(liked_dest_ids) and any(str(lid) in dest_lookup for lid in liked_dest_ids)

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
            safety_threshold = RISK_SAFETY_THRESHOLD.get(risk_tolerance or 3, 0.40)
            if safety < safety_threshold:
                continue  # hard filter
            season = f.get("seasonality", {}).get(travel_month, 0.5)
            cost_index = float(f.get("cost_index", 0.5))
            avg_daily_cost_usd = f.get("avg_daily_cost_usd")
            route_fare = (
                _cached_route_fare(user_profile, dest, f, travel_month, typical_duration_days)
                if include_route_fares
                else None
            )
            route_cost_usd = route_fare.price_usd if route_fare is not None else None
            avg_daily_budget_usd = _avg_daily_budget_usd(
                float(avg_daily_cost_usd) if avg_daily_cost_usd else None,
                cost_index,
                typical_duration_days,
                route_cost_usd,
            )
            crowd_index = f.get("crowd_by_month", {}).get(travel_month, 0.5)
            activities: dict[str, float] = f.get("activities", {})

            act_score = _activity_match_score(vacation_prefs, activities)
            budget_score = _budget_fit_score(
                budget_min_usd,
                budget_max_usd,
                cost_index,
                avg_daily_cost_usd,
                typical_duration_days,
                route_cost_usd,
            )
            safety_sc = _safety_score(safety, risk_tolerance)
            lang_sc = _language_score(f, language_comfort)
            crowd_sc = _crowd_score(crowd_index, crowd_preference)
            climate_sc = _climate_match(f, climate_prefs)

            origin_prox = _origin_proximity_score(origin_lat, origin_lng, dest.get("lat"), dest.get("lng"))
            liked_sim = _liked_destinations_similarity(
                liked_dest_ids,
                dest_id,
                dest.get("region"),
                dest.get("subregion"),
                activities,
                dest_lookup,
            )

            lang_penalty = _language_penalty(f, language_comfort)
            visited_penalty = _liked_visited_penalty(dest_id, liked_dest_ids)

            breakdown: dict[str, float] = {
                "activity_match": round(act_score, 4),
                "budget_fit": round(budget_score, 4),
                "season_fit": round(float(season), 4),
                "visa_effort": round(visa_score, 4),
                "safety_modulation": round(safety_sc, 4),
                "language_match": round(lang_sc, 4),
                "crowd_fit": round(crowd_sc, 4),
                "climate_match": round(climate_sc, 4),
            }
            if lang_penalty < 0:
                breakdown["language_penalty"] = round(lang_penalty, 4)
            if visited_penalty < 0:
                breakdown["liked_visited_penalty"] = round(visited_penalty, 4)
            if origin_prox is not None:
                breakdown["origin_proximity"] = round(origin_prox, 4)
            if liked_sim is not None:
                breakdown["liked_similarity"] = round(liked_sim, 4)

            # Dynamic weight normalisation: optional signals get their weight only when present
            factors: dict[str, float | None] = {
                "activity_match": act_score,
                "liked_dest_similarity": liked_sim if (has_liked_signal and liked_sim is not None) else None,
                "budget_fit": budget_score,
                "origin_proximity": origin_prox,
                "season_fit": float(season),
                "safety_modulation": safety_sc,
                "language_match": lang_sc,
                "visa_effort": visa_score,
                "climate_match": climate_sc,
                "crowd_fit": crowd_sc,
            }

            total_weight = sum(COMPOSITE_WEIGHTS[k] for k, v in factors.items() if v is not None)
            composite = sum(COMPOSITE_WEIGHTS[k] * v for k, v in factors.items() if v is not None) / total_weight

            composite = max(0.0, min(1.0, composite + lang_penalty + visited_penalty))

            tags = _explanation_tags(breakdown, f, visa_score, safety, travel_month)

            results.append(
                ScoredDestination(
                    destination_id=dest_id,
                    name=dest["name"],
                    country_code=dest["country_code"],
                    region=dest.get("region") or "",
                    score=round(composite, 4),
                    score_breakdown=breakdown,
                    explanation_tags=tags,
                    avg_daily_cost_usd=float(avg_daily_cost_usd) if avg_daily_cost_usd else None,
                    avg_daily_budget_usd=round(avg_daily_budget_usd, 2),
                    route_cost_usd=round(route_cost_usd, 2) if route_cost_usd is not None else None,
                    route_cost_source=route_fare.source if route_fare is not None else None,
                    season_score=round(float(season), 4),
                    safety_score=round(safety, 4),
                )
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results
