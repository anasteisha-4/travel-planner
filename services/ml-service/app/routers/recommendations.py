import time
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.models.recommendation_log import RecommendationLog
from app.schemas.recommendation import RecommendRequest, RecommendResponse
from app.services.content_scorer import ContentScorer
from app.services.data_loader import get_all_destinations, get_destination_features

router = APIRouter()

_scorer = ContentScorer()

SCORER_WEIGHTS = {
    "activity_match": 0.28,
    "budget_fit": 0.18,
    "season": 0.18,
    "visa": 0.12,
    "safety": 0.10,
    "language": 0.06,
    "crowd": 0.04,
    "climate": 0.04,
}


@router.post("/recommend", response_model=RecommendResponse)
def get_recommendations(
    request: RecommendRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecommendResponse:
    from app.services.profile_client import _get_profile_sync

    t_start = time.monotonic()

    profile = _get_profile_sync(db, user_id)

    destinations = get_all_destinations(db)
    dest_ids = [uuid.UUID(str(d["id"])) for d in destinations]
    dest_features = get_destination_features(db, dest_ids)

    citizenship = request.citizenship_code.upper()
    if citizenship != "RU":
        _attach_visa_scores(db, dest_ids, dest_features, citizenship)

    filters = {
        "citizenship_code": citizenship,
        "exclude_destination_ids": [uuid.UUID(str(x)) for x in request.exclude_destination_ids],
        "region": request.region,
    }

    scored = _scorer.score(
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
        model_version="content-v1",
        results=top_results,
        latency_ms=latency_ms,
    )

    return RecommendResponse(
        recommendation_id=recommendation_id,
        model_version="content-v1",
        results=top_results,
    )


def _attach_visa_scores(
    db: Session,
    dest_ids: list[uuid.UUID],
    dest_features: dict[uuid.UUID, dict],
    citizenship_code: str,
) -> None:
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT destination_id, visa_score FROM visa_rules "
            "WHERE citizenship_code = :cc AND destination_id = ANY(:ids)"
        ),
        {"cc": citizenship_code, "ids": dest_ids},
    )
    for row in rows:
        k = uuid.UUID(str(row.destination_id))
        if k in dest_features:
            dest_features[k]["visa_score"] = float(row.visa_score)


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
            scorer_weights=SCORER_WEIGHTS,
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
