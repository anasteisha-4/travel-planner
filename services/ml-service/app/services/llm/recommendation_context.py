from app.schemas.recommendation import RecommendRequest, ScoredDestination


def build_recommendation_context(
    *,
    profile: dict,
    request: RecommendRequest,
    citizenship_code: str,
    results: list[ScoredDestination],
) -> dict:
    budget_max_usd = profile.get("budget_max_usd")
    duration_days = profile.get("typical_duration_days")
    budget_max_per_day_usd = (
        float(budget_max_usd) / max(int(duration_days), 1) if budget_max_usd is not None and duration_days else None
    )
    return {
        "user_profile": {
            "origin_city_name": profile.get("origin_city_name"),
            "budget_min_usd": profile.get("budget_min_usd"),
            "budget_max_usd": profile.get("budget_max_usd"),
            "budget_max_per_day_usd": round(budget_max_per_day_usd, 2) if budget_max_per_day_usd is not None else None,
            "typical_duration_days": duration_days,
            "risk_tolerance": profile.get("risk_tolerance"),
            "visa_tolerance": profile.get("visa_tolerance"),
            "language_comfort": profile.get("language_comfort"),
            "climate_preferences": profile.get("climate_preferences"),
            "vacation_preferences_ranked": profile.get("vacation_preferences_ranked"),
            "liked_destination_names": profile.get("liked_destination_names"),
            "rest_level": profile.get("rest_level"),
        },
        "request": {
            "travel_month": request.travel_month,
            "limit": request.limit,
            "region": request.region,
            "citizenship_code": citizenship_code,
            "region_review_note": (
                "Europe filter may include European Russia. Treat Russian destinations as valid only when they fit "
                "the user's actual intent; if the profile points to international, English-speaking, Mediterranean, "
                "or Paris-like travel, flag domestic-Russia dominance as weak preference fit."
            )
            if request.region == "Europe"
            else None,
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
                "estimated_trip_cost_usd": (
                    round(float(item.avg_daily_cost_usd) * max(int(duration_days or 1), 1), 2)
                    if item.avg_daily_cost_usd is not None
                    else None
                ),
                "route_cost_source": item.route_cost_source,
                "season_score": item.season_score,
                "safety_score": item.safety_score,
            }
            for index, item in enumerate(results, start=1)
        ],
    }
