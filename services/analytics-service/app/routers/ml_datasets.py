from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id
from app.models.ml_dataset_snapshot import MLDatasetSnapshot
from app.services.ml_datasets import build_ml_dataset_report, create_snapshot

router = APIRouter(prefix="/api/v1/admin/ml-datasets", tags=["admin-ml-datasets"])


@router.get("/report")
def ml_dataset_report(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    return build_ml_dataset_report(db, date_from, date_to)


@router.get("/snapshots")
def list_snapshots(
    dataset_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    query = db.query(MLDatasetSnapshot)
    if dataset_type:
        query = query.filter(MLDatasetSnapshot.dataset_type == dataset_type)
    snapshots = query.order_by(MLDatasetSnapshot.created_at.desc()).limit(limit).all()
    return {"snapshots": [_snapshot_to_dict(snapshot) for snapshot in snapshots]}


@router.post("/snapshots")
def build_snapshot(
    dataset_type: Literal["all", "ranker", "budget", "itinerary"] = "all",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    snapshot = create_snapshot(db, dataset_type, date_from, date_to, str(user_id))
    return _snapshot_to_dict(snapshot)


def _snapshot_to_dict(snapshot: MLDatasetSnapshot) -> dict:
    return {
        "id": str(snapshot.id),
        "dataset_type": snapshot.dataset_type,
        "date_from": snapshot.date_from.isoformat() if snapshot.date_from else None,
        "date_to": snapshot.date_to.isoformat() if snapshot.date_to else None,
        "contract_version": snapshot.contract_version,
        "builder_version": snapshot.builder_version,
        "row_count": snapshot.row_count,
        "positive_count": snapshot.positive_count,
        "storage_path": snapshot.storage_path,
        "metadata": snapshot.metadata_json or {},
        "sanity_report": snapshot.sanity_report or {},
        "created_by_user_id": snapshot.created_by_user_id,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }
