"""Generate LTR training pairs for LambdaRank training.

Creates (query, document, label) tuples where:
  - query    = synthetic user profile
  - document = destination
  - label    = relevance grade 0..3 from INDEPENDENT quality signals
               (NOT from content_scorer — avoids circular labels)

Label sources (all objective, independent of content_scorer):
  1. Seasonality       — absolute season_score for travel_month       (35%)
  2. Safety fit        — against user risk_tolerance threshold         (25%)
  3. Visa fit          — hard constraint from visa_tolerance           (20%)
  4. Value-for-money   — log(pageviews) / cost_index                   (10%)
  5. Climate match     — is_coastal / has_mountains vs climate_prefs   (5%)
  6. Crowd fit         — crowd_index vs crowd_preference               (5%)

ContentScorer is used ONLY for sampling (top-20% → ensure positive signal
in query group). Labels are computed independently after sampling.

Usage:
    python scripts/generate_ltr_pairs.py [--n-profiles 3000] [--dests-per-query 150]
"""

import argparse
import json
import logging
import os
import random
import sys
import uuid
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.content_scorer import ContentScorer  # noqa: E402  (used for sampling only)
from app.services.data_loader import get_all_destinations, get_destination_features  # noqa: E402

ACTIVITY_TYPES = [
    "beach",
    "culture",
    "active",
    "nature",
    "food",
    "shopping",
    "nightlife",
    "family",
    "romance",
    "business",
]
ACTIVITY_TYPE_MAP = {
    "beach": "beach",
    "culture": "culture",
    "adventure": "active",
    "active": "active",
    "nature": "nature",
    "food": "food",
    "shopping": "shopping",
    "nightlife": "nightlife",
    "family": "family",
    "romance": "romance",
    "wellness": "romance",
    "urban": "culture",
    "business": "business",
}
VISA_OPTIONS = ["visa_free_only", "evisa_ok", "any_visa", "any_visa"]
DURATION_OPTIONS = ["weekend", "short", "standard", "long", "extended"]
CLIMATE_OPTIONS = ["tropical_warm", "mediterranean", "continental_mild", "cold_snow", "dry_desert", "any"]
LANGUAGE_OPTIONS = [["ru"], ["en"], ["ru", "en"], ["any"]]

BUDGET_TIERS = {
    "budget": (200, 800),
    "mid": (800, 2500),
    "premium": (2500, 6000),
    "luxury": (6000, 20000),
}

MONTHS_WEIGHTS = [1, 1, 1, 2, 2, 3, 3, 3, 2, 2, 1, 1]  # summer-biased
MONTHS_CDF = np.cumsum(MONTHS_WEIGHTS) / sum(MONTHS_WEIGHTS)

rng = random.Random(42)
np_rng = np.random.default_rng(42)


def _activity_vector(activities: dict[str, float]) -> np.ndarray:
    return np.array([float(activities.get(a, 0.0)) for a in ACTIVITY_TYPES], dtype=np.float64)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _activity_preference_score(profile: dict, dest_features: dict) -> float:
    activities = dest_features.get("activities", {})
    vacation_prefs: list[str] = profile.get("vacation_preferences_ranked") or []
    total, weights = 0.0, 0.0
    for rank, act in enumerate(vacation_prefs[:5], start=1):
        activity_key = ACTIVITY_TYPE_MAP.get(act, act)
        w = float(6 - rank)
        total += w * float(activities.get(activity_key, 0.0))
        weights += w
    return total / weights if weights > 0 else 0.0


def _liked_destination_score(
    profile: dict,
    dest_id: uuid.UUID,
    dest_features: dict,
    liked_context: dict,
) -> tuple[float, float]:
    liked_vec = np.array(liked_context.get("liked_activity_vector") or [], dtype=np.float64)
    dest_vec = _activity_vector(dest_features.get("activities", {}))
    likes_activity_sim = _cosine_similarity(liked_vec, dest_vec) if liked_vec.size else 0.0
    dest_subregion = dest_features.get("subregion")
    liked_id_set = set(str(x) for x in profile.get("liked_destination_ids", []))
    likes_same_subregion = float(
        bool(dest_subregion)
        and dest_subregion in (liked_context.get("liked_subregions") or [])
        and str(dest_id) not in liked_id_set
    )
    return likes_activity_sim, likes_same_subregion


def _build_liked_context(
    profile: dict,
    profile_idx: int,
    all_destinations: list[dict],
    feat_by_id: dict[uuid.UUID, dict],
) -> dict:
    """Create stable synthetic liked destinations without perturbing profile RNG."""
    local_rng = random.Random(10_000 + profile_idx)
    candidates: list[tuple[float, uuid.UUID, dict]] = []
    for dest in all_destinations:
        dest_id = uuid.UUID(str(dest["id"]))
        feat = feat_by_id.get(dest_id, {})
        score = _activity_preference_score(profile, feat)
        score += 0.05 * float(feat.get("safety_score", 0.5))
        if score > 0:
            candidates.append((score, dest_id, dest))

    if not candidates:
        return {"liked_destination_ids": [], "liked_activity_vector": [], "liked_subregions": []}

    candidates.sort(key=lambda x: x[0], reverse=True)
    pool = candidates[: min(30, len(candidates))]
    n_liked = local_rng.choices([0, 1, 2, 3], weights=[20, 35, 30, 15])[0]
    if n_liked == 0:
        return {"liked_destination_ids": [], "liked_activity_vector": [], "liked_subregions": []}

    liked = local_rng.sample(pool, min(n_liked, len(pool)))
    liked_ids = [str(dest_id) for _, dest_id, _ in liked]
    liked_vecs = [_activity_vector(feat_by_id[dest_id].get("activities", {})) for _, dest_id, _ in liked]
    liked_subregions = [
        str(feat_by_id[dest_id].get("subregion")) for _, dest_id, _ in liked if feat_by_id[dest_id].get("subregion")
    ]
    mean_vec = np.mean(liked_vecs, axis=0).round(6).tolist() if liked_vecs else []

    return {
        "liked_destination_ids": liked_ids,
        "liked_activity_vector": mean_vec,
        "liked_subregions": sorted(set(liked_subregions)),
    }


def sample_month() -> int:
    r = rng.random()
    for i, v in enumerate(MONTHS_CDF):
        if r <= v:
            return i + 1
    return 6


def make_profile() -> dict:
    """Generate realistic synthetic user profile with all 12 fields."""
    n_prefs = rng.randint(2, 5)
    vacation_prefs = rng.sample(ACTIVITY_TYPES, n_prefs)

    budget_tier = rng.choices(["budget", "mid", "premium", "luxury"], weights=[25, 40, 25, 10])[0]
    b_min, b_max = BUDGET_TIERS[budget_tier]
    budget_min = rng.uniform(b_min, b_min + (b_max - b_min) * 0.4)
    budget_max = budget_min + rng.uniform(budget_min * 0.3, budget_min * 1.2)

    typical_duration = rng.choices(DURATION_OPTIONS, weights=[10, 30, 35, 20, 5])[0]
    typical_duration_days = {"weekend": 2, "short": 5, "standard": 10, "long": 21, "extended": 45}[typical_duration]

    risk_tolerance = rng.choices([1, 2, 3, 4, 5], weights=[10, 20, 35, 25, 10])[0]
    visa_tolerance = rng.choices(VISA_OPTIONS, weights=[25, 30, 30, 15])[0]
    language_comfort = rng.choice(LANGUAGE_OPTIONS)

    crowd_preference = rng.choices([1, 2, 3, 4, 5], weights=[15, 20, 30, 25, 10])[0]

    n_climate = rng.randint(0, 3)
    climate_prefs = rng.sample(CLIMATE_OPTIONS[:-1], min(n_climate, len(CLIMATE_OPTIONS) - 1))
    if not climate_prefs or rng.random() < 0.2:
        climate_prefs = ["any"]

    # Optional origin city (lat/lng pair — used for proximity feature)
    origin_city = rng.choice(
        [
            None,  # 50% no origin
            None,
            None,
            None,
            None,
            (55.75, 37.62),  # Moscow
            (59.95, 30.32),  # Saint Petersburg
            (56.83, 60.60),  # Yekaterinburg
            (43.11, 131.90),  # Vladivostok
            (48.48, 135.08),  # Khabarovsk
            (51.18, 71.45),  # Astana (KZ)
            (41.30, 69.24),  # Tashkent (UZ)
            (50.45, 30.52),  # Kyiv (UA)
            (48.86, 2.35),  # Paris (FR)
            (51.51, -0.13),  # London (GB)
            (40.71, -74.01),  # New York (US)
            (35.69, 139.69),  # Tokyo (JP)
            (1.35, 103.82),  # Singapore (SG)
            (-23.55, -46.63),  # Sao Paulo (BR)
            (28.61, 77.21),  # Delhi (IN)
        ]
    )
    origin_lat = origin_city[0] if origin_city else None
    origin_lng = origin_city[1] if origin_city else None

    return {
        "vacation_preferences_ranked": vacation_prefs,
        "budget_min_usd": round(budget_min, 2),
        "budget_max_usd": round(budget_max, 2),
        "budget_tier": budget_tier,
        "typical_duration": typical_duration,
        "typical_duration_days": typical_duration_days,
        "risk_tolerance": risk_tolerance,
        "visa_tolerance": visa_tolerance,
        "language_comfort": language_comfort,
        "crowd_preference": crowd_preference,
        "climate_preferences": climate_prefs,
        "liked_destination_ids": [],  # populated during pair generation
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
    }


# ---------------------------------------------------------------------------
# INDEPENDENT quality score — no dependency on ContentScorer
# ---------------------------------------------------------------------------


def independent_quality_score(
    profile: dict,
    dest_features: dict,
    travel_month: int,
    dest_id: uuid.UUID | None = None,
) -> float:
    """Relevance score that REQUIRES user profile to compute.

    Every component is a user×dest INTERACTION — the same destination gets
    different scores for different user profiles. Without knowing the profile,
    a model cannot predict labels from dest features alone.

    This is the key fix vs the original circular-label problem: instead of
    pure dest-quality signals (season, safety, visa as absolutes), we compute
    genuine user preference fit:

      activity_fit  0.30  user ranked prefs × dest activity scores (weighted)
      budget_fit    0.23  avg_daily_cost × duration vs user budget range
      safety_fit    0.18  safety_score vs user risk_tolerance threshold
      visa_fit      0.12  visa_score vs user visa_tolerance strictness
      liked_fit     0.10  similarity to destinations the profile liked
      crowd_fit     0.07  crowd_index[month] vs user crowd_preference

    Season is intentionally excluded — it's a dest-only signal available as
    season_01..12 in dest features. LightGBM discovers its interaction with
    u_month_sin/cos naturally via tree splits.
    """
    score = 0.0

    # 1. Activity match (30%) — weighted by rank: 1st pref → weight 5, 5th → weight 1
    activities = dest_features.get("activities", {})
    vacation_prefs: list[str] = profile.get("vacation_preferences_ranked") or []
    act_total, w_total = 0.0, 0.0
    for rank, act in enumerate(vacation_prefs[:5], start=1):
        act_score = float(activities.get(act, 0.0))
        w = float(6 - rank)
        act_total += w * act_score
        w_total += w
    activity_fit = act_total / w_total if w_total > 0 else 0.3
    score += activity_fit * 0.30

    # 2. Budget fit (23%) — trip_cost = avg_daily × duration_days vs [budget_min, budget_max]
    avg_daily = float(dest_features.get("avg_daily_cost_usd") or 80.0)
    budget_min = float(profile.get("budget_min_usd") or 200)
    budget_max = float(profile.get("budget_max_usd") or 2000)
    duration_days = int(profile.get("typical_duration_days") or 10)
    trip_cost = avg_daily * duration_days
    if budget_min <= trip_cost <= budget_max:
        budget_fit = 1.0
    elif trip_cost < budget_min:
        budget_fit = max(0.3, 1.0 - (budget_min - trip_cost) / max(budget_min, 1) * 0.5)
    else:
        budget_fit = max(0.0, 1.0 - (trip_cost - budget_max) / max(budget_max, 1))
    score += budget_fit * 0.23

    # 3. Safety fit (18%) — threshold depends on user risk_tolerance
    safety = float(dest_features.get("safety_score", 0.5))
    risk = int(profile.get("risk_tolerance", 3))
    safety_threshold = {1: 0.70, 2: 0.55, 3: 0.40, 4: 0.20, 5: 0.0}[risk]
    safety_fit = 1.0 if safety >= safety_threshold else max(0.0, safety / max(safety_threshold, 0.01))
    score += safety_fit * 0.18

    # 4. Visa fit (12%) — threshold depends on user visa_tolerance
    visa = float(dest_features.get("visa_score", 0.5))
    visa_tol = str(profile.get("visa_tolerance", "any_visa"))
    visa_threshold = {"visa_free_only": 0.80, "evisa_ok": 0.55, "any_visa": 0.0}.get(visa_tol, 0.0)
    visa_fit = 1.0 if visa >= visa_threshold else max(0.0, visa / max(visa_threshold, 0.01))
    score += visa_fit * 0.12

    # 5. Liked destinations fit (10%) — activity cosine + subregion affinity
    liked_context = {
        "liked_activity_vector": profile.get("liked_activity_vector") or [],
        "liked_subregions": profile.get("liked_subregions") or [],
    }
    liked_sim, liked_same_subregion = _liked_destination_score(
        profile,
        dest_id or uuid.UUID(int=0),
        dest_features,
        liked_context,
    )
    liked_fit = min(1.0, 0.75 * liked_sim + 0.25 * liked_same_subregion)
    if profile.get("liked_destination_ids"):
        score += liked_fit * 0.10
    else:
        score += 0.05

    # 6. Crowd fit (7%) — depends on user crowd_preference
    crowd_pref = float(profile.get("crowd_preference", 3)) / 5.0
    crowd_by_month = dest_features.get("crowd_by_month", {})
    crowd_dest = float(crowd_by_month.get(travel_month, 0.5) if crowd_by_month else 0.5)
    crowd_fit = 1.0 - abs(crowd_pref - crowd_dest)
    score += crowd_fit * 0.07

    # Small noise (σ=0.05) — enough to prevent memorisation, small enough not to
    # overwhelm the genuine user×dest signal
    noise = rng.gauss(0.0, 0.05)
    score = max(0.0, min(1.0, score + noise))

    return round(score, 6)


def score_to_label(score: float, scores_in_query: list[float]) -> int:
    """Convert continuous independent score → relevance grade 0..3.

    Uses per-query quantiles so label distribution is always balanced
    within each query group (required for LambdaRank).
    """
    arr = np.array(scores_in_query)
    q25, q50, q75 = np.percentile(arr, [25, 50, 75])
    if score >= q75:
        return 3
    if score >= q50:
        return 2
    if score >= q25:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Pair generation
# ---------------------------------------------------------------------------


def generate_pairs(
    db,
    n_profiles: int,
    dests_per_query: int,
) -> list[dict]:
    # ContentScorer used ONLY for sampling top destinations (positive signal)
    content_scorer = ContentScorer()

    logger.info("Loading destinations and features …")
    all_destinations = get_all_destinations(db)
    all_dest_ids = [uuid.UUID(str(d["id"])) for d in all_destinations]
    dest_features = get_destination_features(db, all_dest_ids)
    logger.info("Loaded %d destinations", len(all_destinations))

    # Build fast lookup: dest_id → features dict
    feat_by_id: dict[uuid.UUID, dict] = {
        uuid.UUID(str(d["id"])): dest_features.get(uuid.UUID(str(d["id"])), {}) for d in all_destinations
    }

    all_pairs: list[dict] = []

    for profile_idx in range(n_profiles):
        query_id = uuid.uuid4()
        profile = make_profile()
        travel_month = sample_month()

        liked_context = _build_liked_context(profile, profile_idx, all_destinations, feat_by_id)
        profile.update(liked_context)

        # Use ContentScorer only to identify top-scoring destinations for positive sampling.
        # Labels are computed INDEPENDENTLY below — ContentScorer scores are NOT used as labels.
        filters: dict = {"exclude_destination_ids": [], "region": None}
        content_ranked = content_scorer.score(
            user_profile=profile,
            destinations=all_destinations,
            dest_features=dest_features,
            travel_month=travel_month,
            filters=filters,
        )

        if len(content_ranked) < 10:
            continue

        # Sample: top-20% (diverse positives) + random 80% (negatives + hard negatives)
        n_top = max(5, dests_per_query // 5)
        top_ranked = content_ranked[:n_top]
        rest_ranked = content_ranked[n_top:]

        n_random = min(dests_per_query - len(top_ranked), len(rest_ranked))
        random_ranked = rng.sample(rest_ranked, n_random)

        selected = top_ranked + random_ranked
        rng.shuffle(selected)

        # Compute INDEPENDENT quality scores for each selected destination
        indep_scores = []
        for sd in selected:
            dest_id = uuid.UUID(str(sd.destination_id))
            feat = feat_by_id.get(dest_id, {})
            iq = independent_quality_score(profile, feat, travel_month, dest_id)
            indep_scores.append(iq)

        # Convert to labels using per-query quantiles
        labels = [score_to_label(s, indep_scores) for s in indep_scores]

        for sd, iq, label in zip(selected, indep_scores, labels, strict=True):
            all_pairs.append(
                {
                    "query_id": str(query_id),
                    "destination_id": str(sd.destination_id),
                    "relevance_label": label,
                    "content_score": round(iq, 6),  # store independent score, not content_scorer score
                    "profile_snapshot": json.dumps(
                        {
                            "vacation_preferences_ranked": profile["vacation_preferences_ranked"],
                            "budget_tier": profile["budget_tier"],
                            "budget_min_usd": profile["budget_min_usd"],
                            "budget_max_usd": profile["budget_max_usd"],
                            "typical_duration": profile["typical_duration"],
                            "typical_duration_days": profile["typical_duration_days"],
                            "risk_tolerance": profile["risk_tolerance"],
                            "visa_tolerance": profile["visa_tolerance"],
                            "language_comfort": profile["language_comfort"],
                            "crowd_preference": profile["crowd_preference"],
                            "climate_preferences": profile["climate_preferences"],
                            "liked_destination_ids": profile["liked_destination_ids"],
                            "liked_activity_vector": profile["liked_activity_vector"],
                            "liked_subregions": profile["liked_subregions"],
                            "origin_lat": profile["origin_lat"],
                            "origin_lng": profile["origin_lng"],
                        }
                    ),
                    "travel_month": travel_month,
                }
            )

        if (profile_idx + 1) % 100 == 0:
            recent = all_pairs[-(len(selected) * 100) :]
            from collections import Counter

            dist = dict(Counter(p["relevance_label"] for p in recent))
            logger.info(
                "Profile %d/%d — pairs: %d, recent labels: %s", profile_idx + 1, n_profiles, len(all_pairs), dist
            )

    return all_pairs


def _score_to_tier(budget_min: float, budget_max: float) -> str:
    mid = (budget_min + budget_max) / 2
    if mid < 800:
        return "budget"
    if mid < 2500:
        return "mid"
    if mid < 6000:
        return "premium"
    return "luxury"


def save_pairs(db, pairs: list[dict]) -> None:
    logger.info("Clearing old ltr_training_pairs …")
    db.execute(text("DELETE FROM ltr_training_pairs"))
    db.commit()

    logger.info("Inserting %d pairs in batches …", len(pairs))
    batch_size = 1000
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i : i + batch_size]
        db.execute(
            text(
                "INSERT INTO ltr_training_pairs "
                "(query_id, destination_id, relevance_label, content_score, profile_snapshot, travel_month) "
                "VALUES (:query_id, :destination_id, :relevance_label, :content_score, :profile_snapshot, :travel_month)"
            ),
            batch,
        )
        db.commit()
        if (i // batch_size + 1) % 20 == 0:
            logger.info("  inserted %d / %d", i + len(batch), len(pairs))

    logger.info("Done — %d pairs saved", len(pairs))


def print_stats(pairs: list[dict]) -> None:
    from collections import Counter

    labels = [p["relevance_label"] for p in pairs]
    label_dist = Counter(labels)
    scores = [p["content_score"] for p in pairs]
    query_ids = set(p["query_id"] for p in pairs)

    logger.info("=== Dataset statistics ===")
    logger.info("Total pairs:    %d", len(pairs))
    logger.info("Unique queries: %d", len(query_ids))
    logger.info("Pairs/query:    %.1f avg", len(pairs) / len(query_ids))
    logger.info("Label dist:     %s", dict(sorted(label_dist.items())))
    logger.info("Indep score:    min=%.3f  mean=%.3f  max=%.3f", min(scores), sum(scores) / len(scores), max(scores))

    # Verify label balance per query (critical for LambdaRank quality)
    query_label_map: dict = {}
    for p in pairs:
        qid = p["query_id"]
        query_label_map.setdefault(qid, set()).add(p["relevance_label"])

    queries_with_positives = sum(1 for v in query_label_map.values() if max(v) >= 2)
    queries_with_all_labels = sum(1 for v in query_label_map.values() if len(v) >= 3)
    logger.info(
        "Queries with label≥2: %d / %d (%.1f%%)",
        queries_with_positives,
        len(query_ids),
        100 * queries_with_positives / len(query_ids),
    )
    logger.info(
        "Queries with ≥3 distinct labels: %d / %d (%.1f%%)",
        queries_with_all_labels,
        len(query_ids),
        100 * queries_with_all_labels / len(query_ids),
    )

    logger.info(
        "Expected best_iteration after training: 150-300 (vs 53 with circular labels — higher = genuine learning)"
    )


def main(n_profiles: int, dests_per_query: int) -> None:
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    logger.info(
        "Generating %d profiles × ~%d dests with INDEPENDENT labels (no circular dependency)",
        n_profiles,
        dests_per_query,
    )

    with SessionLocal() as db:
        pairs = generate_pairs(db, n_profiles=n_profiles, dests_per_query=dests_per_query)
        print_stats(pairs)
        save_pairs(db, pairs)

    logger.info("Generation complete: %d pairs total", len(pairs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n-profiles", type=int, default=3000, help="Number of synthetic user profiles (default 3000 for stable NDCG)"
    )
    parser.add_argument("--dests-per-query", type=int, default=150, help="Destinations per query group (default 150)")
    args = parser.parse_args()
    main(n_profiles=args.n_profiles, dests_per_query=args.dests_per_query)
