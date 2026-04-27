import time
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.models.recommendation_log import RecommendationLog
from app.schemas.recommendation import RecommendRequest, RecommendResponse
from app.services.content_scorer import BaseScorer, ContentScorer
from app.services.data_loader import get_all_destinations, get_destination_features
from app.services.experiment import get_variant
from app.services.profile_client import _get_profile_sync
from app.services.ranker_scorer import LTRScorer, get_active_scorer

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


def _select_scorer(request: RecommendRequest, db: Session, user_id: uuid.UUID) -> tuple[BaseScorer, str]:
    """Return (scorer, model_version_str).

    Priority:
    1. Explicit model_version in request body (for manual testing).
    2. A/B experiment assignment (scorer_ab).
    3. Active LTR model from registry, fallback to content.
    """
    if request.model_version == "content-v1":
        return _content_scorer, "content-v1"

    if request.model_version is None:
        try:
            variant = get_variant(db, user_id, "scorer_ab")
            if variant == "content-v1":
                return _content_scorer, "content-v1"
        except Exception:
            pass

    scorer = get_active_scorer(db)
    version = "ltr-v1" if isinstance(scorer, LTRScorer) else "content-v1"
    return scorer, version


@router.post("/recommend", response_model=RecommendResponse)
def get_recommendations(
    request: RecommendRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecommendResponse:
    t_start = time.monotonic()

    profile = _get_profile_sync(db, user_id)

    destinations = get_all_destinations(db)
    dest_ids = [uuid.UUID(str(d["id"])) for d in destinations]
    citizenship = request.citizenship_code.upper()
    dest_features = get_destination_features(db, dest_ids, citizenship_code=citizenship)

    filters = {
        "citizenship_code": citizenship,
        "exclude_destination_ids": [uuid.UUID(str(x)) for x in request.exclude_destination_ids],
        "region": request.region,
    }

    scorer, model_version = _select_scorer(request, db, user_id)
    scored = scorer.score(
        user_profile=profile,
        destinations=destinations,
        dest_features=dest_features,
        travel_month=request.travel_month,
        filters=filters,
    )

    top_results = scored[: request.limit]
    latency_ms = int((time.monotonic() - t_start) * 1000)
    recommendation_id = uuid.uuid4()

    _log_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        user_id=user_id,
        request=request,
        model_version=model_version,
        results=top_results,
        latency_ms=latency_ms,
    )

    return RecommendResponse(
        recommendation_id=recommendation_id,
        model_version=model_version,
        results=top_results,
    )


def _log_recommendation(
    db: Session,
    recommendation_id: uuid.UUID,
    user_id: uuid.UUID,
    request: RecommendRequest,
    model_version: str,
    results: list,
    latency_ms: int,
) -> None:
    try:
        scorer_weights = (
            CONTENT_SCORER_WEIGHTS
            if model_version == "content-v1"
            else {"model_type": "lambdarank", "objective": "lambdarank", "metric": "ndcg"}
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
            },
            model_version=model_version,
            scorer_weights=scorer_weights,
            results=[
                {
                    "destination_id": str(r.destination_id),
                    "name": r.name,
                    "score": r.score,
                    "score_breakdown": r.score_breakdown,
                }
                for r in results
            ],
            latency_ms=latency_ms,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
