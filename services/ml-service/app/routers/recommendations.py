import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user_id
from app.lib.russian_names import translate_destination_name
from app.models.recommendation_log import RecommendationLog
from app.schemas.llm_quality import LLMReviewIssue, LLMReviewSeverity, LLMReviewStatus
from app.schemas.recommendation import (
    RecommendDestinationRequest,
    RecommendRequest,
    RecommendResponse,
    ScoredDestination,
)
from app.services.analytics_events import emit_ml_quality_event
from app.services.content_scorer import BaseScorer, ContentScorer
from app.services.currency import convert_usd, normalize_currency
from app.services.data_loader import get_all_destinations, get_destination_features
from app.services.llm.quality_gate import LLMQualityGate
from app.services.llm.recommendation_adjustment_policy import apply_recommendation_quality_review
from app.services.llm.recommendation_context import build_recommendation_context
from app.services.profile_client import _get_profile_sync
from app.services.ranker_scorer import LTRScorer, get_active_scorer, get_scorer_by_version
from app.services.travel_advisory import filter_destinations_by_travel_advisory

router = APIRouter()

CONTENT_SCORER_WEIGHTS = {
    "activity_match": 0.28,
    "budget_fit": 0.18,
    "season": 0.18,
    "visa": 0.12,
    "safety": 0.10,
    "language": 0.06,
    "crowd": 0.04,
    "climate": 0.04,
}

_content_scorer = ContentScorer()


def _select_scorer(request: RecommendRequest, db: Session) -> tuple[BaseScorer, str]:
    """Return (scorer, model_version_str).

    Priority:
    1. Explicit model_version in request body (for manual testing).
    2. Active LTR model from registry, fallback to content.
    """
    if request.model_version == "content-v1":
        return _content_scorer, "content-v1"
    if request.model_version:
        scorer = get_scorer_by_version(db, request.model_version)
        if scorer is not None:
            return scorer, scorer.version

    scorer = get_active_scorer(db)
    version = scorer.version if isinstance(scorer, LTRScorer) else "content-v1"
    return scorer, version


def _with_display_currency(
    item: ScoredDestination,
    display_currency: str,
    *,
    request_region: str | None = None,
) -> ScoredDestination:
    display_region = "Middle East" if request_region == "Middle East" else item.region
    return item.model_copy(
        update={
            "name": item.display_name or item.name_ru or translate_destination_name(item.name),
            "name_original": item.name_original or item.name,
            "name_ru": item.name_ru or translate_destination_name(item.name),
            "display_name": item.display_name or item.name_ru or translate_destination_name(item.name),
            "region": display_region,
            "avg_daily_cost": convert_usd(item.avg_daily_cost_usd, display_currency),
            "avg_daily_cost_currency": display_currency,
            "avg_daily_budget": convert_usd(item.avg_daily_budget_usd or item.avg_daily_cost_usd, display_currency),
            "avg_daily_budget_currency": display_currency,
        }
    )


@router.post("/recommend", response_model=RecommendResponse)
def get_recommendations(
    request: RecommendRequest,
    authorization: str | None = Header(default=None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecommendResponse:
    t_start = time.monotonic()

    profile = _get_profile_sync(db, user_id)
    display_currency = normalize_currency(profile.get("preferred_currency"))

    destinations = get_all_destinations(db)
    citizenship = request.citizenship_code.upper()
    destinations, advisory_blocked = filter_destinations_by_travel_advisory(
        destinations=destinations,
        citizenship_code=citizenship,
    )
    dest_ids = [uuid.UUID(str(d["id"])) for d in destinations]
    dest_features = get_destination_features(db, dest_ids, citizenship_code=citizenship)

    filters = {
        "citizenship_code": citizenship,
        "exclude_destination_ids": [uuid.UUID(str(x)) for x in request.exclude_destination_ids],
        "region": request.region,
        "include_route_fares": False,
    }

    scorer, model_version = _select_scorer(request, db)
    scored = scorer.score(
        user_profile=profile,
        destinations=destinations,
        dest_features=dest_features,
        travel_month=request.travel_month,
        filters=filters,
    )
    scored = _apply_country_diversity(scored, region=request.region, limit=max(request.limit * 4, request.limit + 20))

    candidate_pool_size = min(len(scored), max(request.limit * 3, request.limit + 10))
    candidate_pool = [
        _with_display_currency(item, display_currency, request_region=request.region)
        for item in scored[:candidate_pool_size]
    ]
    top_results = candidate_pool[: request.limit]
    recommendation_id = uuid.uuid4()
    quality_review = None
    applied_adjustments: list[dict] = []
    ignored_adjustments: list[dict] = []

    if settings.LLM_QUALITY_ENABLED:
        context = build_recommendation_context(
            profile=profile,
            request=request,
            citizenship_code=citizenship,
            results=candidate_pool[
                : min(len(candidate_pool), max(request.limit, settings.LLM_RECOMMENDATION_REVIEW_LIMIT))
            ],
        )
        quality_review = LLMQualityGate().review_recommendations(
            db=db,
            user_id=user_id,
            recommendation_id=recommendation_id,
            context=context,
        )
        quality_review = _enforce_recommendation_review_sanity(quality_review, request, profile, top_results)
        adjustment_result = apply_recommendation_quality_review(
            top_results,
            quality_review,
            replacement_pool=candidate_pool[request.limit :],
        )
        top_results = _apply_country_diversity(
            adjustment_result.results,
            region=request.region,
            limit=request.limit,
        )
        applied_adjustments = adjustment_result.applied_adjustments
        ignored_adjustments = adjustment_result.ignored_adjustments
        final_quality_review = _review_after_adjustments(
            quality_review,
            applied_adjustments,
            ignored_adjustments,
        )
        quality_review = final_quality_review
        _emit_llm_review_events(
            quality_review=quality_review,
            recommendation_id=recommendation_id,
            applied_adjustments=applied_adjustments,
            ignored_adjustments=ignored_adjustments,
            authorization=authorization,
        )

    latency_ms = int((time.monotonic() - t_start) * 1000)

    _log_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        user_id=user_id,
        request=request,
        model_version=model_version,
        results=top_results,
        latency_ms=latency_ms,
        quality_review=quality_review,
        applied_adjustments=applied_adjustments,
        ignored_adjustments=ignored_adjustments,
        advisory_blocked=advisory_blocked,
    )

    public_results = [item.model_copy(update={"quality_review": None}) for item in top_results]

    return RecommendResponse(
        recommendation_id=recommendation_id,
        model_version=model_version,
        quality_model_version=_public_quality_model_version(quality_review),
        quality_review=None,
        results=public_results,
    )


@router.post("/recommend/destination", response_model=ScoredDestination)
def get_destination_recommendation_score(
    request: RecommendDestinationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ScoredDestination:
    profile = _get_profile_sync(db, user_id)
    display_currency = normalize_currency(profile.get("preferred_currency"))

    destinations = [
        destination
        for destination in get_all_destinations(db)
        if uuid.UUID(str(destination["id"])) == request.destination_id
    ]
    if not destinations:
        raise HTTPException(status_code=404, detail="Destination not found")

    citizenship = request.citizenship_code.upper()
    dest_features = get_destination_features(db, [request.destination_id], citizenship_code=citizenship)
    filters = {
        "citizenship_code": citizenship,
        "exclude_destination_ids": [],
        "region": None,
    }

    scorer_request = RecommendRequest(
        travel_month=request.travel_month,
        limit=1,
        citizenship_code=citizenship,
        model_version=request.model_version,
    )
    scorer, _model_version = _select_scorer(scorer_request, db)
    scored = scorer.score(
        user_profile=profile,
        destinations=destinations,
        dest_features=dest_features,
        travel_month=request.travel_month,
        filters=filters,
    )
    if not scored:
        relaxed_profile = {
            **profile,
            "visa_tolerance": "any_visa",
            "risk_tolerance": 5,
        }
        scored = _content_scorer.score(
            user_profile=relaxed_profile,
            destinations=destinations,
            dest_features=dest_features,
            travel_month=request.travel_month,
            filters=filters,
        )
    if not scored:
        raise HTTPException(status_code=404, detail="Destination score not available")

    return _with_display_currency(scored[0], display_currency)


def _log_recommendation(
    db: Session,
    recommendation_id: uuid.UUID,
    user_id: uuid.UUID,
    request: RecommendRequest,
    model_version: str,
    results: list,
    latency_ms: int,
    quality_review,
    applied_adjustments: list[dict],
    ignored_adjustments: list[dict],
    advisory_blocked: list[dict] | None = None,
) -> None:
    try:
        scorer_weights = (
            CONTENT_SCORER_WEIGHTS
            if model_version == "content-v1"
            else {
                "model_type": "lambdarank",
                "objective": "lambdarank",
                "metric": "ndcg",
                "candidate_generator": "content-scorer",
                "candidate_top_n": 200,
            }
        )
        log = RecommendationLog(
            id=recommendation_id,
            user_id=user_id,
            request={
                "travel_month": request.travel_month,
                "limit": request.limit,
                "region": request.region,
                "citizenship_code": request.citizenship_code,
                "exclude_destination_ids": [str(x) for x in request.exclude_destination_ids],
                "llm_quality": _recommendation_log_quality_payload(
                    quality_review=quality_review,
                    applied_adjustments=applied_adjustments,
                    ignored_adjustments=ignored_adjustments,
                ),
                "travel_advisory": {
                    "blocked_count": len(advisory_blocked or []),
                    "blocked_sample": (advisory_blocked or [])[:20],
                },
            },
            model_version=model_version,
            scorer_weights=scorer_weights,
            results=[
                {
                    "destination_id": str(r.destination_id),
                    "name": r.name,
                    "rank": index,
                    "score": r.score,
                    "reason_tags": r.explanation_tags,
                    "factor_breakdown": r.score_breakdown,
                    "route_cost_source": r.route_cost_source,
                    "llm_status": (r.quality_review or quality_review).status.value
                    if (r.quality_review or quality_review)
                    else None,
                    "llm_issue_codes": [issue.code for issue in (r.quality_review or quality_review).issues]
                    if (r.quality_review or quality_review)
                    else [],
                    "llm_adjustment": [
                        adjustment.model_dump(mode="json") for adjustment in r.quality_review.suggested_adjustments
                    ]
                    if r.quality_review
                    else [],
                    "llm_review_id": str((r.quality_review or quality_review).review_id)
                    if (r.quality_review or quality_review) and (r.quality_review or quality_review).review_id
                    else None,
                }
                for index, r in enumerate(results, start=1)
            ],
            latency_ms=latency_ms,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()


def _apply_country_diversity(
    results: list[ScoredDestination],
    *,
    region: str | None,
    limit: int,
) -> list[ScoredDestination]:
    if not results or limit <= 0:
        return results

    normalized_region = (region or "").strip().casefold()
    if normalized_region in {"asia", "europe"}:
        max_per_country = 2
    elif normalized_region == "middle east":
        max_per_country = 4
    else:
        max_per_country = 3

    selected: list[ScoredDestination] = []
    country_counts: dict[str, int] = {}
    deferred: list[ScoredDestination] = []

    for item in results:
        country_code = (item.country_code or "").upper()
        if country_counts.get(country_code, 0) < max_per_country:
            selected.append(item)
            country_counts[country_code] = country_counts.get(country_code, 0) + 1
        else:
            deferred.append(item)
        if len(selected) >= limit:
            return selected

    selected.extend(deferred[: max(0, limit - len(selected))])
    return selected


def _emit_llm_review_events(
    *,
    quality_review,
    recommendation_id: uuid.UUID,
    applied_adjustments: list[dict],
    ignored_adjustments: list[dict],
    authorization: str | None,
) -> None:
    issue_codes = [issue.code for issue in quality_review.issues] if quality_review else []
    context = {
        "provider": quality_review.provider,
        "model": quality_review.model,
        "prompt_version": quality_review.prompt_version,
        "status": quality_review.status.value,
        "issue_codes": issue_codes,
        "critical_count": sum(1 for issue in quality_review.issues if issue.severity.value == "critical"),
        "warning_count": sum(1 for issue in quality_review.issues if issue.severity.value == "warning"),
        "review_id": str(quality_review.review_id) if quality_review.review_id else None,
        "applied_adjustments": applied_adjustments,
        "ignored_adjustments": ignored_adjustments,
    }
    event_type = "llm_quality_skipped" if quality_review.status.value == "skipped" else "llm_quality_review_completed"
    emit_ml_quality_event(
        event_type,
        context,
        entity_type="recommendation_set",
        entity_id=recommendation_id,
        authorization=authorization,
    )
    if applied_adjustments:
        emit_ml_quality_event(
            "llm_quality_adjustment_applied",
            context,
            entity_type="recommendation_set",
            entity_id=recommendation_id,
            authorization=authorization,
        )


def _review_after_adjustments(quality_review, applied: list[dict], ignored: list[dict]):
    if quality_review is None:
        return None
    if quality_review.status.value in {"caution", "reject"} and applied and not ignored:
        return quality_review.model_copy(
            update={
                "user_summary_ru": "Рекомендации скорректированы по результатам проверки.",
                "defense_trace": f"{quality_review.defense_trace or ''} Applied all LLM recommendation adjustments.".strip(),
            }
        )
    return quality_review


def _public_quality_model_version(quality_review) -> str | None:
    if quality_review is None or quality_review.status == LLMReviewStatus.skipped:
        return None
    return quality_review.model or settings.LLM_MODEL


def _recommendation_log_quality_payload(
    *,
    quality_review,
    applied_adjustments: list[dict],
    ignored_adjustments: list[dict],
) -> dict | None:
    if quality_review is None:
        return None
    return {
        "status": quality_review.status.value,
        "provider": quality_review.provider,
        "model": quality_review.model,
        "prompt_version": quality_review.prompt_version,
        "review_id": str(quality_review.review_id) if quality_review.review_id else None,
        "issue_codes": [issue.code for issue in quality_review.issues],
        "suggested_adjustments": [
            adjustment.model_dump(mode="json") for adjustment in quality_review.suggested_adjustments
        ],
        "applied_adjustments": applied_adjustments,
        "ignored_adjustments": ignored_adjustments,
    }


def _enforce_recommendation_review_sanity(
    quality_review,
    request: RecommendRequest,
    profile: dict,
    top_results: list[ScoredDestination],
):
    if quality_review is None or quality_review.status in {LLMReviewStatus.skipped, LLMReviewStatus.failed}:
        return quality_review

    quality_review = _drop_invalid_budget_issues(quality_review, profile, top_results)
    issues = list(quality_review.issues)
    if _is_beach_sensitive_request(request, profile):
        for item in top_results[:5]:
            if "beach" in item.explanation_tags:
                continue
            if not _needs_beach_fit_guardrail(item):
                continue
            issues.append(
                LLMReviewIssue(
                    code="beach_fit_guardrail",
                    severity=LLMReviewSeverity.warning,
                    message="Top destination lacks a current-season beach scenario for a beach-focused request.",
                    destination_id=item.destination_id,
                )
            )
    if _is_international_europe_sensitive_request(request, profile, top_results):
        for item in top_results:
            if item.country_code != "RU":
                continue
            issues.append(
                LLMReviewIssue(
                    code="international_europe_fit_guardrail",
                    severity=LLMReviewSeverity.warning,
                    message=(
                        "Domestic Russia is a weak fit for an English-speaking, Mediterranean, Paris-like Europe request."
                    ),
                    destination_id=item.destination_id,
                )
            )
    if not issues:
        return quality_review
    return quality_review.model_copy(
        update={
            "status": LLMReviewStatus.caution,
            "issues": issues,
            "defense_trace": f"{quality_review.defense_trace or ''} Backend contract guardrail added beach-fit issues.".strip(),
        }
    )


def _drop_invalid_budget_issues(
    quality_review,
    profile: dict,
    top_results: list[ScoredDestination],
):
    budget_max_usd = profile.get("budget_max_usd")
    duration_days = profile.get("typical_duration_days")
    if budget_max_usd is None or not duration_days:
        return quality_review

    by_id = {item.destination_id: item for item in top_results}
    invalid_budget_target_ids: set[uuid.UUID] = set()
    kept_issues: list[LLMReviewIssue] = []
    for issue in quality_review.issues:
        target_id = issue.destination_id or issue.target_id or issue.item_id
        if target_id and _is_invalid_budget_issue(
            issue, by_id.get(target_id), float(budget_max_usd), int(duration_days)
        ):
            invalid_budget_target_ids.add(target_id)
            continue
        kept_issues.append(issue)

    if not invalid_budget_target_ids:
        return quality_review

    kept_adjustments = [
        adjustment
        for adjustment in quality_review.suggested_adjustments
        if (adjustment.target_destination_id or adjustment.target_id) not in invalid_budget_target_ids
    ]
    status = quality_review.status
    if not kept_issues and status in {LLMReviewStatus.caution, LLMReviewStatus.reject}:
        status = LLMReviewStatus.ok

    return quality_review.model_copy(
        update={
            "status": status,
            "issues": kept_issues,
            "suggested_adjustments": kept_adjustments,
            "defense_trace": (
                f"{quality_review.defense_trace or ''} Backend ignored invalid LLM budget issue(s)."
            ).strip(),
        }
    )


def _is_invalid_budget_issue(
    issue: LLMReviewIssue,
    item: ScoredDestination | None,
    budget_max_usd: float,
    duration_days: int,
) -> bool:
    if item is None or item.avg_daily_cost_usd is None:
        return False
    code = issue.code.casefold()
    if "budget" not in code and "cost" not in code:
        return False
    estimated_total = float(item.avg_daily_cost_usd) * max(duration_days, 1)
    if item.route_cost_usd is not None:
        estimated_total += float(item.route_cost_usd)
    return estimated_total <= budget_max_usd


def _is_beach_sensitive_request(request: RecommendRequest, profile: dict) -> bool:
    preferences = [
        str(item.get("value") if isinstance(item, dict) else item).lower()
        for item in (profile.get("vacation_preferences_ranked") or [])
    ]
    climate = [str(item).lower() for item in (profile.get("climate_preferences") or [])]
    wants_warm = not climate or any(item in {"mediterranean", "tropical_warm", "any"} for item in climate)
    return "beach" in preferences[:3] and wants_warm and request.travel_month in {4, 5, 6, 7, 8, 9}


def _needs_beach_fit_guardrail(item: ScoredDestination) -> bool:
    cold_or_inland_country = item.country_code in {"RU", "SE", "FI", "NO", "BY", "MD", "RS", "BA", "CZ", "SK"}
    return cold_or_inland_country or item.region in {"Americas", "Oceania"}


def _is_international_europe_sensitive_request(
    request: RecommendRequest,
    profile: dict,
    top_results: list[ScoredDestination],
) -> bool:
    if request.region != "Europe":
        return False
    top_five = top_results[:5]
    if sum(1 for item in top_five if item.country_code == "RU") < 3:
        return False
    languages = {str(item).lower() for item in (profile.get("language_comfort") or [])}
    climate = {str(item).lower() for item in (profile.get("climate_preferences") or [])}
    liked_names = " ".join(str(item).lower() for item in (profile.get("liked_destination_names") or []))
    preferences = {
        str(item.get("value") if isinstance(item, dict) else item).lower()
        for item in (profile.get("vacation_preferences_ranked") or [])
    }
    english_only = "en" in languages and "ru" not in languages and "any" not in languages
    international_signal = english_only or "mediterranean" in climate or "paris" in liked_names
    return international_signal and bool({"beach", "culture", "shopping"} & preferences)
