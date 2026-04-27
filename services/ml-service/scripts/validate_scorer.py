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
        "typical_duration_days": 5,
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
        "typical_duration_days": 10,
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
        "typical_duration_days": 10,
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
        "typical_duration_days": 5,
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
        "typical_duration_days": 2,
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
        return sum((2**s - 1) / math.log2(i + 2) for i, s in enumerate(scores[:k]))

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
        print(f"\n{'─' * 72}")
        print(f"  Profile: {profile['name']}")
        print(f"  Prefs: {profile['vacation_preferences_ranked'][:3]}...")
        print(
            f"  Budget: ${profile['budget_min_usd']}–${profile['budget_max_usd']} USD ({profile['typical_duration']})"
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
        print(f"  {'─' * 3} {'─' * 6} {'─' * 29} {'─' * 5} {'─' * 30}")

        for i, r in enumerate(results[:10], 1):
            tags = ", ".join(r.explanation_tags[:3])
            print(f"  {i:<3} {r.score:<7.4f} {r.name:<30} {r.country_code:<6} {tags}")

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
            ranked_relevance = [synthetic_labels.get(str(r.destination_id), 0.0) for r in results[:10]]
            ideal_relevance = sorted(synthetic_labels.values(), reverse=True)[:10]
            ndcg = ndcg_at_k(ranked_relevance, ideal_relevance, k=10)
            all_ndcg.append(ndcg)
            print(f"\n  NDCG@10 vs synthetic labels: {ndcg:.4f}")
        else:
            print("\n  (synthetic labels not available — skipping NDCG)")

    # Summary
    if all_ndcg:
        print("\n" + "=" * 72)
        print(f"  Mean NDCG@10 across {len(all_ndcg)} profiles: {sum(all_ndcg) / len(all_ndcg):.4f}")
        print(f"  Min: {min(all_ndcg):.4f}  Max: {max(all_ndcg):.4f}")
        if sum(all_ndcg) / len(all_ndcg) >= 0.35:
            print("  ✓ Content scorer baseline is sane (NDCG@10 ≥ 0.35)")
        else:
            print("  ✗ Low NDCG — review scoring weights or data coverage")

    # Liked similarity acceptance tests
    print("\n" + "─" * 72)
    print("Liked similarity acceptance tests:")
    _run_liked_similarity_checks(scorer, destinations, dest_features, TRAVEL_MONTH)

    # Origin proximity acceptance tests
    print("\n" + "─" * 72)
    print("Origin proximity acceptance tests:")
    _run_origin_proximity_checks(scorer, destinations, dest_features, TRAVEL_MONTH)

    # Language penalty acceptance tests
    print("\n" + "─" * 72)
    print("Language penalty acceptance tests:")
    _run_language_penalty_checks(scorer, destinations, dest_features, TRAVEL_MONTH)

    # Sanity checks
    print("\n" + "─" * 72)
    print("Sanity checks:")

    _run_sanity_checks(scorer, destinations, dest_features, TRAVEL_MONTH)

    db.close()


# SPb: lat=59.95, lng=30.32 → Santiago CL ~13400km, Hawaii US ~9700km, Bangkok ~7600km
SPB_LAT, SPB_LNG = 59.95, 30.32
# within 5000km from SPb: Turkey, Caucasus, Balkans, Central Asia
NEAR_SPB_COUNTRIES = {"TR", "GE", "AM", "AZ", "UZ", "KZ", "KG", "TJ", "RS", "ME", "BA", "MK", "AL", "BG", "RO", "HR", "SI", "HU", "SK", "CZ", "AT", "DE", "PL", "FI", "SE", "NO", "DK", "EE", "LV", "LT", "BY", "UA", "MD", "EG", "TN", "MA", "IL", "JO", "LB", "CY", "GR", "MT", "IT", "ES", "PT", "FR", "BE", "NL", "LU", "CH", "LI", "IS", "IE", "GB", "RU"}
FAR_SPB_COUNTRIES = {"CL", "US", "AU", "NZ", "JP", "KR", "CN", "BR", "AR", "PE", "MX", "ZA", "NG"}


def _run_origin_proximity_checks(scorer, destinations, dest_features, travel_month) -> None:
    base_profile = {
        "vacation_preferences_ranked": ["beach", "culture", "food", "nature", "urban"],
        "budget_min_usd": 500,
        "budget_max_usd": 5000,
        "typical_duration_days": 10,
        "risk_tolerance": 3,
        "visa_tolerance": "any_visa",
        "language_comfort": ["any"],
        "crowd_preference": 3,
        "climate_preferences": ["any"],
        "liked_destination_ids": [],
        "onboarding_completed": True,
    }
    filters = {"citizenship_code": "RU", "exclude_destination_ids": [], "region": None}

    # Test 1: origin=СПб → far destinations (Santiago, Hawaii) not in top-20
    profile_spb = {**base_profile, "origin_lat": SPB_LAT, "origin_lng": SPB_LNG}
    results_spb = scorer.score(profile_spb, destinations, dest_features, travel_month, filters)
    top20_spb = results_spb[:20]
    far_in_top20 = [(r.name, r.country_code) for r in top20_spb if r.country_code in FAR_SPB_COUNTRIES]
    status = "✓" if not far_in_top20 else f"✗ far destinations leaked: {far_in_top20}"
    print(f"  origin=SPb → no far (>10k km) in top-20:    {status}")

    # Test 2: origin=СПб → at least 5 within 5000km in top-10
    near_in_top10 = sum(1 for r in top20_spb[:10] if r.country_code in NEAR_SPB_COUNTRIES)
    status = "✓" if near_in_top10 >= 5 else f"✗ only {near_in_top10}/10"
    print(f"  origin=SPb → ≥5 within 5000km in top-10:    {status} ({near_in_top10}/10)")
    if near_in_top10 < 5:
        print(f"    Top-10: {[(r.name, r.country_code) for r in top20_spb[:10]]}")
    else:
        near = [(r.name, r.country_code) for r in top20_spb[:10] if r.country_code in NEAR_SPB_COUNTRIES]
        print(f"    Near matches: {near}")

    # Test 3: no origin → breakdown has no origin_proximity key
    profile_no_origin = {**base_profile, "origin_lat": None, "origin_lng": None}
    results_no_origin = scorer.score(profile_no_origin, destinations, dest_features, travel_month, filters)
    has_prox_key = any("origin_proximity" in r.score_breakdown for r in results_no_origin[:5])
    status = "✓ (no origin_proximity key)" if not has_prox_key else "✗ unexpected origin_proximity in breakdown"
    print(f"  no origin → no origin_proximity in breakdown: {status}")

    # Show breakdown for top SPb result
    if results_spb:
        top = results_spb[0]
        prox = top.score_breakdown.get("origin_proximity", "N/A")
        print(f"  Top result for SPb: {top.name} ({top.country_code}), origin_proximity={prox}, score={top.score}")


MOROCCAN_CITIES = {"Fes", "Marrakech", "Casablanca", "Rabat", "Tangier", "Agadir", "Fez"}
# EN-speaking cities — either native-EN or high english_speaking_score
ENGLISH_CITIES = {"London", "Paris", "Amsterdam", "Berlin", "Barcelona", "Rome", "Vienna", "Prague", "Budapest",
                  "Brisbane", "Sydney", "Melbourne", "Dublin", "Edinburgh", "Cape Town", "Toronto", "Auckland"}


def _run_language_penalty_checks(scorer, destinations, dest_features, travel_month) -> None:
    base_profile = {
        "vacation_preferences_ranked": ["culture", "urban", "food", "nature", "beach"],
        "budget_min_usd": 500,
        "budget_max_usd": 5000,
        "typical_duration_days": 10,
        "risk_tolerance": 3,
        "visa_tolerance": "any_visa",
        "crowd_preference": 3,
        "climate_preferences": ["any"],
        "liked_destination_ids": [],
        "origin_lat": None,
        "origin_lng": None,
        "onboarding_completed": True,
    }
    filters = {"citizenship_code": "RU", "exclude_destination_ids": [], "region": None}

    # Test 1: language=["ru"] → Moroccan cities not in top-30
    profile_ru = {**base_profile, "language_comfort": ["ru"]}
    results_ru = scorer.score(profile_ru, destinations, dest_features, travel_month, filters)
    top30_names_ru = {r.name for r in results_ru[:30]}
    leaked = MOROCCAN_CITIES & top30_names_ru
    status = "✓" if not leaked else f"✗ leaked: {leaked}"
    print(f"  lang=[ru] → Moroccan cities not in top-30:    {status}")

    # Test 2: language=["ru","en"] → at least one major European city in top-20
    profile_ru_en = {**base_profile, "language_comfort": ["ru", "en"]}
    results_ru_en = scorer.score(profile_ru_en, destinations, dest_features, travel_month, filters)
    top20_names_en = {r.name for r in results_ru_en[:20]}
    en_hits = ENGLISH_CITIES & top20_names_en
    status = "✓" if en_hits else "✗ no major EN city in top-20"
    print(f"  lang=[ru,en] → EN cities in top-20:           {status} ({en_hits})")

    # Test 3: language=["any"] → no language_penalty key in breakdown
    profile_any = {**base_profile, "language_comfort": ["any"]}
    results_any = scorer.score(profile_any, destinations, dest_features, travel_month, filters)
    has_penalty_key = any("language_penalty" in r.score_breakdown for r in results_any[:10])
    status = "✓ (no penalty key)" if not has_penalty_key else "✗ unexpected penalty in breakdown"
    print(f"  lang=[any] → no language_penalty in breakdown: {status}")

    # Show Fes score for ru profile (should be heavily penalised)
    fes = next((r for r in results_ru if r.name in ("Fes", "Fez")), None)
    if fes:
        pen = fes.score_breakdown.get("language_penalty", 0)
        rank = next(i for i, r in enumerate(results_ru, 1) if r.destination_id == fes.destination_id)
        print(f"  Fes rank for lang=[ru]: #{rank}, score={fes.score}, penalty={pen}")


NIZHNY_NOVGOROD_ID = "a0b28ab3-0a05-42ce-a7c6-2cdbc133a1d2"
BALI_ID = "e751b485-190e-4f93-9620-9e486bfc92b2"

# Destinations expected in top-10 when liked=Nizhny Novgorod (RU + CIS Russian-speaking)
LIKED_NN_EXPECTED_COUNTRIES = {"RU", "BY", "KZ", "UZ", "KG", "GE", "AM", "AZ", "MD", "TJ"}
# Destinations expected in top-10 when liked=Bali (tropical South/SE Asia)
LIKED_BALI_EXPECTED = {"TH", "VN", "PH", "LK", "MY", "KH", "MM", "ID", "MV"}


def _run_liked_similarity_checks(scorer, destinations, dest_features, travel_month) -> None:
    base_profile = {
        "vacation_preferences_ranked": ["beach", "culture", "food", "nature", "urban"],
        "budget_min_usd": 500,
        "budget_max_usd": 3000,
        "typical_duration_days": 10,
        "risk_tolerance": 3,
        "visa_tolerance": "any_visa",
        "language_comfort": ["any"],
        "crowd_preference": 3,
        "climate_preferences": ["any"],
        "origin_lat": None,
        "origin_lng": None,
        "onboarding_completed": True,
    }
    filters = {"citizenship_code": "RU", "exclude_destination_ids": [], "region": None}

    # Test 1: liked=Nizhny Novgorod → expect CIS/post-Soviet cities in top-10
    profile_nn = {**base_profile, "liked_destination_ids": [NIZHNY_NOVGOROD_ID]}
    results_nn = scorer.score(profile_nn, destinations, dest_features, travel_month, filters)
    top10_nn = results_nn[:10]
    cis_in_top10 = sum(1 for r in top10_nn if r.country_code in LIKED_NN_EXPECTED_COUNTRIES)
    status = "✓" if cis_in_top10 >= 2 else f"✗ only {cis_in_top10}"
    print(f"  liked=Nizhny Novgorod → CIS/RU-speaking in top-10: {status} ({cis_in_top10}/10)")
    if cis_in_top10 < 2:
        print(f"    Top-10: {[(r.name, r.country_code) for r in top10_nn]}")
    else:
        matches = [(r.name, r.country_code) for r in top10_nn if r.country_code in LIKED_NN_EXPECTED_COUNTRIES]
        print(f"    Matches: {matches}")

    # Test 2: liked=Bali → expect SE/S Asian tropical destinations in top-10
    profile_bali = {**base_profile, "liked_destination_ids": [BALI_ID]}
    results_bali = scorer.score(profile_bali, destinations, dest_features, travel_month, filters)
    top10_bali = results_bali[:10]
    asia_in_top10 = sum(1 for r in top10_bali if r.country_code in LIKED_BALI_EXPECTED)
    status = "✓" if asia_in_top10 >= 2 else f"✗ only {asia_in_top10}"
    print(f"  liked=Bali → SE/S Asian tropical in top-10:        {status} ({asia_in_top10}/10)")
    if asia_in_top10 < 2:
        print(f"    Top-10: {[(r.name, r.country_code) for r in top10_bali]}")
    else:
        matches = [(r.name, r.country_code) for r in top10_bali if r.country_code in LIKED_BALI_EXPECTED]
        print(f"    Matches: {matches}")

    # Test 3: no liked → results should exist and be well-distributed
    profile_no_liked = {**base_profile, "liked_destination_ids": []}
    results_no_liked = scorer.score(profile_no_liked, destinations, dest_features, travel_month, filters)
    has_liked_breakdown = any("liked_similarity" in r.score_breakdown for r in results_no_liked[:5])
    status = "✓ (no liked_similarity key)" if not has_liked_breakdown else "✗ unexpected liked_similarity in breakdown"
    print(f"  no liked → no liked_similarity in breakdown:        {status}")

    # Show liked_similarity breakdown for top result
    if results_nn:
        top = results_nn[0]
        sim_val = top.score_breakdown.get("liked_similarity", "N/A")
        print(f"  Top result for liked=NN: {top.name} ({top.country_code}), liked_similarity={sim_val}, score={top.score}")


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
    non_compliant = [r for r in results_strict if dest_features.get(r.destination_id, {}).get("visa_score", 0) < 0.80]
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
    top5_coastal = sum(1 for r in beach_results[:5] if dest_features.get(r.destination_id, {}).get("is_coastal", False))
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
