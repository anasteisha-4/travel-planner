"""Scorer validation script — Phase 3.4.

Runs ContentScorer against live DB for 5 synthetic user profiles and
prints ranked results + NDCG@10 vs synthetic label_score baseline.

Usage (from repo root):
    docker compose run --rm ml-service python scripts/validate_scorer.py
"""

import math
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.content_scorer import ContentScorer
from app.services.data_loader import get_all_destinations, get_destination_features

# ---------------------------------------------------------------------------
# Test profiles (mimic onboarding v2 answers)
# ---------------------------------------------------------------------------
TEST_PROFILES = [
    {
        "name": "Пляжник-бюджетник (RU)",
        "vacation_preferences_ranked": ["beach", "food", "culture", "nature", "urban"],
        "budget_min_usd": 500,
        "budget_max_usd": 1500,
        "typical_duration": "short",
        "risk_tolerance": 3,
        "visa_tolerance": "visa_free_only",
        "language_comfort": ["ru"],
        "crowd_preference": 3,
        "climate_preferences": ["tropical_warm", "mediterranean"],
        "liked_destination_ids": [],
        "origin_lat": 55.75,
        "origin_lng": 37.62,
        "onboarding_completed": True,
    },
    {
        "name": "Лыжник-авантюрист",
        "vacation_preferences_ranked": ["adventure", "nature", "culture", "beach", "urban"],
        "budget_min_usd": 2000,
        "budget_max_usd": 6000,
        "typical_duration": "standard",
        "risk_tolerance": 4,
        "visa_tolerance": "evisa_ok",
        "language_comfort": ["ru", "en"],
        "crowd_preference": 2,
        "climate_preferences": ["cold_snow"],
        "liked_destination_ids": [],
        "origin_lat": 55.75,
        "origin_lng": 37.62,
        "onboarding_completed": True,
    },
    {
        "name": "Культурный турист (EN)",
        "vacation_preferences_ranked": ["culture", "urban", "food", "wellness", "shopping"],
        "budget_min_usd": 3000,
        "budget_max_usd": 10000,
        "typical_duration": "standard",
        "risk_tolerance": 2,
        "visa_tolerance": "any_visa",
        "language_comfort": ["en"],
        "crowd_preference": 4,
        "climate_preferences": ["mediterranean", "continental_mild"],
        "liked_destination_ids": [],
        "origin_lat": None,
        "origin_lng": None,
        "onboarding_completed": True,
    },
    {
        "name": "Тихий отдых на природе",
        "vacation_preferences_ranked": ["nature", "wellness", "beach", "adventure", "culture"],
        "budget_min_usd": 800,
        "budget_max_usd": 2500,
        "typical_duration": "short",
        "risk_tolerance": 2,
        "visa_tolerance": "visa_free_only",
        "language_comfort": ["ru"],
        "crowd_preference": 1,
        "climate_preferences": ["tropical_warm"],
        "liked_destination_ids": [],
        "origin_lat": 55.75,
        "origin_lng": 37.62,
        "onboarding_completed": True,
    },
    {
        "name": "Ночная жизнь и шоппинг",
        "vacation_preferences_ranked": ["nightlife", "shopping", "urban", "food", "culture"],
        "budget_min_usd": 1500,
        "budget_max_usd": 5000,
        "typical_duration": "weekend",
        "risk_tolerance": 3,
        "visa_tolerance": "evisa_ok",
        "language_comfort": ["any"],
        "crowd_preference": 5,
        "climate_preferences": ["any"],
        "liked_destination_ids": [],
        "origin_lat": 55.75,
        "origin_lng": 37.62,
        "onboarding_completed": True,
    },
]


def ndcg_at_k(ranked_scores: list[float], ideal_scores: list[float], k: int = 10) -> float:
    """NDCG@k: relevance = synthetic label_score from DB."""
    def dcg(scores: list[float]) -> float:
        return sum(
            (2 ** s - 1) / math.log2(i + 2)
            for i, s in enumerate(scores[:k])
        )
    dcg_val = dcg(ranked_scores)
    idcg_val = dcg(sorted(ideal_scores, reverse=True))
    return dcg_val / idcg_val if idcg_val > 0 else 0.0


def load_synthetic_labels(db_session) -> dict[str, float]:
    """Load label_score from user_preference_profiles for sanity cross-check.
    Returns {destination_id_str: avg_label_score}.
    """
    try:
        rows = db_session.execute(
            text(
                "SELECT label_destination_id, label_score "
                "FROM user_preference_profiles "
                "WHERE label_destination_id IS NOT NULL AND label_score IS NOT NULL "
                "LIMIT 5000"
            )
        ).fetchall()
        label_map: dict[str, list[float]] = {}
        for row in rows:
            did = str(row.label_destination_id)
            score = float(row.label_score)
            label_map.setdefault(did, []).append(score)
        return {k: sum(v) / len(v) for k, v in label_map.items()}
    except Exception as e:
        print(f"  (warning: could not load synthetic labels: {e})")
        return {}


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    print("Loading destinations and features...")
    destinations = get_all_destinations(db)
    dest_ids = [uuid.UUID(str(d["id"])) for d in destinations]
    dest_features = get_destination_features(db, dest_ids)
    print(f"  → {len(destinations)} active destinations, features loaded")

    synthetic_labels = load_synthetic_labels(db)
    print(f"  → {len(synthetic_labels)} synthetic label scores loaded")

    scorer = ContentScorer()
    TRAVEL_MONTH = 7  # July

    print("\n" + "=" * 72)
    all_ndcg: list[float] = []

    for profile in TEST_PROFILES:
        print(f"\n{'─'*72}")
        print(f"  Profile: {profile['name']}")
        print(f"  Prefs: {profile['vacation_preferences_ranked'][:3]}...")
        print(
            f"  Budget: ${profile['budget_min_usd']}–${profile['budget_max_usd']} USD "
            f"({profile['typical_duration']})"
        )
        print(
            f"  Filters: visa={profile['visa_tolerance']}, "
            f"risk={profile['risk_tolerance']}, lang={profile['language_comfort']}"
        )

        filters = {
            "citizenship_code": "RU",
            "exclude_destination_ids": [],
            "region": None,
        }

        results = scorer.score(
            user_profile=profile,
            destinations=destinations,
            dest_features=dest_features,
            travel_month=TRAVEL_MONTH,
            filters=filters,
        )

        print(f"\n  Top 10 for July (of {len(results)} candidates):")
        print(f"  {'#':<3} {'Score':<7} {'Name':<30} {'Country':<6} {'Tags'}")
        print(f"  {'─'*3} {'─'*6} {'─'*29} {'─'*5} {'─'*30}")

        for i, r in enumerate(results[:10], 1):
            tags = ", ".join(r.explanation_tags[:3])
            print(
                f"  {i:<3} {r.score:<7.4f} {r.name:<30} {r.country_code:<6} {tags}"
            )

        # Score breakdown for top result
        if results:
            top = results[0]
            bd = top.score_breakdown
            print(f"\n  Breakdown for #{1}: {top.name}")
            for k, v in sorted(bd.items(), key=lambda x: -x[1]):
                bar = "█" * int(v * 20)
                print(f"    {k:<20} {v:.3f}  {bar}")

        # NDCG@10 against synthetic labels
        if synthetic_labels:
            ranked_relevance = [
                synthetic_labels.get(str(r.destination_id), 0.0)
                for r in results[:10]
            ]
            ideal_relevance = sorted(synthetic_labels.values(), reverse=True)[:10]
            ndcg = ndcg_at_k(ranked_relevance, ideal_relevance, k=10)
            all_ndcg.append(ndcg)
            print(f"\n  NDCG@10 vs synthetic labels: {ndcg:.4f}")
        else:
            print("\n  (synthetic labels not available — skipping NDCG)")

    # Summary
    if all_ndcg:
        print("\n" + "=" * 72)
        print(f"  Mean NDCG@10 across {len(all_ndcg)} profiles: {sum(all_ndcg)/len(all_ndcg):.4f}")
        print(f"  Min: {min(all_ndcg):.4f}  Max: {max(all_ndcg):.4f}")
        if sum(all_ndcg) / len(all_ndcg) >= 0.35:
            print("  ✓ Content scorer baseline is sane (NDCG@10 ≥ 0.35)")
        else:
            print("  ✗ Low NDCG — review scoring weights or data coverage")

    # Sanity checks
    print("\n" + "─" * 72)
    print("Sanity checks:")

    _run_sanity_checks(scorer, destinations, dest_features, TRAVEL_MONTH)

    db.close()


def _run_sanity_checks(scorer, destinations, dest_features, travel_month):
    # 1. Visa-free filter should exclude destinations with visa_required
    profile_strict = {
        **TEST_PROFILES[0],
        "visa_tolerance": "visa_free_only",
    }
    results_strict = scorer.score(
        user_profile=profile_strict,
        destinations=destinations,
        dest_features=dest_features,
        travel_month=travel_month,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    non_compliant = [
        r for r in results_strict
        if dest_features.get(r.destination_id, {}).get("visa_score", 0) < 0.80
    ]
    status = "✓" if not non_compliant else f"✗ {len(non_compliant)} visa violations"
    print(f"  Visa-free hard filter:        {status}")

    # 2. Beach profile should have is_coastal destinations in top-5
    beach_results = scorer.score(
        user_profile=TEST_PROFILES[0],
        destinations=destinations,
        dest_features=dest_features,
        travel_month=travel_month,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    top5_coastal = sum(
        1 for r in beach_results[:5]
        if dest_features.get(r.destination_id, {}).get("is_coastal", False)
    )
    status = "✓" if top5_coastal >= 2 else f"✗ only {top5_coastal}/5 coastal in top-5"
    print(f"  Beach profile coastal top-5:  {status} ({top5_coastal}/5 coastal)")

    # 3. Region filter should restrict results
    region_results = scorer.score(
        user_profile=TEST_PROFILES[2],
        destinations=destinations,
        dest_features=dest_features,
        travel_month=travel_month,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": "Europe"},
    )
    non_europe = [r for r in region_results if r.region != "Europe"]
    status = "✓" if not non_europe else f"✗ {len(non_europe)} non-Europe leaked"
    print(f"  Region filter (Europe):       {status} ({len(region_results)} results)")

    # 4. Exclude IDs should remove from results
    if destinations:
        excl_id = uuid.UUID(str(destinations[0]["id"]))
        excl_results = scorer.score(
            user_profile=TEST_PROFILES[0],
            destinations=destinations,
            dest_features=dest_features,
            travel_month=travel_month,
            filters={
                "citizenship_code": "RU",
                "exclude_destination_ids": [excl_id],
                "region": None,
            },
        )
        leaked = any(r.destination_id == excl_id for r in excl_results)
        status = "✓" if not leaked else "✗ excluded ID found in results"
        print(f"  Exclude destination_id:       {status}")

    # 5. Score range [0, 1]
    all_scores = [r.score for r in beach_results]
    in_range = all(0.0 <= s <= 1.0 for s in all_scores)
    status = "✓" if in_range else "✗ out-of-range scores found"
    print(f"  All scores in [0, 1]:         {status}")

    # 6. Score diversity (not all equal)
    if len(all_scores) > 5:
        spread = max(all_scores) - min(all_scores)
        status = f"✓ spread={spread:.3f}" if spread > 0.05 else f"✗ too narrow spread={spread:.3f}"
        print(f"  Score diversity:              {status}")


if __name__ == "__main__":
    main()
