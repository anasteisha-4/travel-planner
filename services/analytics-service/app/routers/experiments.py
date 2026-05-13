from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id, get_optional_user_id
from app.models.feature_flag import Experiment
from app.schemas.experiments import ExperimentAssignmentsResponse, ExperimentReportResponse, ExperimentResponse
from app.services.experiments import build_experiment_report, get_assignments

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])
admin_router = APIRouter(prefix="/api/v1/admin/experiments", tags=["admin-experiments"])


@router.get("/assignments", response_model=ExperimentAssignmentsResponse)
def get_experiment_assignments(
    user_id=Depends(get_optional_user_id),
    x_anonymous_id: str | None = Header(default=None, alias="X-Anonymous-ID"),
    db: Session = Depends(get_db),
) -> ExperimentAssignmentsResponse:
    assignments = get_assignments(db, user_id=user_id, anonymous_id=x_anonymous_id)
    return ExperimentAssignmentsResponse(
        assignments={
            key: {
                "experiment_key": key,
                "variant": variant,
            }
            for key, variant in assignments.items()
        }
    )


@admin_router.get("", response_model=list[ExperimentResponse])
def list_experiments(
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
) -> list[ExperimentResponse]:
    return list(db.query(Experiment).order_by(Experiment.key.asc()).all())


@admin_router.get("/{experiment_key}/report", response_model=ExperimentReportResponse)
def experiment_report(
    experiment_key: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
) -> ExperimentReportResponse:
    return ExperimentReportResponse(experiment_key=experiment_key, variants=build_experiment_report(db, experiment_key))
