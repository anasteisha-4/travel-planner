from app.schemas.recommendation import RecommendRequest, ScoredDestination


def build_recommendation_context(
    *,
    profile: dict,
    request: RecommendRequest,
    citizenship_code: str,
    results: list[ScoredDestination],
) -> dict:
    return {
        "user_profile": {
            "origin_city_name": profile.get("origin_city_name"),
            "budget_min_usd": profile.get("budget_min_usd"),
            "budget_max_usd": profile.get("budget_max_usd"),
            "typical_duration_days": profile.get("typical_duration_days"),
            "risk_tolerance": profile.get("risk_tolerance"),
            "visa_tolerance": profile.get("visa_tolerance"),
            "language_comfort": profile.get("language_comfort"),
            "climate_preferences": profile.get("climate_preferences"),
            "vacation_preferences_ranked": profile.get("vacation_preferences_ranked"),
        },
        "request": {
            "travel_month": request.travel_month,
            "limit": request.limit,
            "region": request.region,
            "citizenship_code": citizenship_code,
        },
        "recommendations": [
            {
                "rank": index,
                "destination_id": str(item.destination_id),
                "name": item.name,
                "country_code": item.country_code,
                "region": item.region,
                "score": item.score,
                "score_breakdown": item.score_breakdown,
                "explanation_tags": item.explanation_tags,
                "avg_daily_cost_usd": item.avg_daily_cost_usd,
                "route_cost_source": item.route_cost_source,
                "season_score": item.season_score,
                "safety_score": item.safety_score,
            }
            for index, item in enumerate(results, start=1)
        ],
    }
