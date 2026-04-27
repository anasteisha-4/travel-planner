from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.model_registry import ModelRegistry
from app.schemas.budget import ModelVersionResponse

router = APIRouter()


@router.get("/models/versions", response_model=list[ModelVersionResponse])
def get_model_versions(db: Session = Depends(get_db)) -> list[ModelVersionResponse]:
    models = db.query(ModelRegistry).order_by(ModelRegistry.created_at.desc()).all()
    return [
        ModelVersionResponse(
            id=str(m.id),
            name=m.name,
            version=m.version,
            model_type=m.model_type,
            is_active=m.is_active,
            metrics=m.metrics,
            trained_at=m.trained_at,
            created_at=m.created_at,
        )
        for m in models
    ]
