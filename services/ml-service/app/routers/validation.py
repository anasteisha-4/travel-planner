import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id

router = APIRouter()


class ValidateTripRequest(BaseModel):
    destination_id: uuid.UUID
    citizenship_code: str = "RU"
    travel_month: int = Field(..., ge=1, le=12)
    budget_per_day_usd: float | None = None


class ValidationWarning(BaseModel):
    type: str
    severity: str  # "high" | "medium" | "low"
    message: str


class ValidateTripResponse(BaseModel):
    destination_id: uuid.UUID
    warnings: list[ValidationWarning]
    info: dict


@router.post("/validate", response_model=ValidateTripResponse)
def validate_trip(
    request: ValidateTripRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ValidateTripResponse:
    dest_id = str(request.destination_id)
    warnings: list[ValidationWarning] = []
    info: dict = {}

    # --- Visa check ---
    visa_row = db.execute(
        text(
            "SELECT visa_type, visa_score, max_stay_days FROM visa_rules "
            "WHERE destination_id = :did AND citizenship_code = :cc"
        ),
        {"did": dest_id, "cc": request.citizenship_code.upper()},
    ).fetchone()

    if visa_row:
        info["visa_type"] = str(visa_row.visa_type)
        info["visa_score"] = float(visa_row.visa_score)
        if visa_row.max_stay_days:
            info["max_stay_days"] = int(visa_row.max_stay_days)
        if float(visa_row.visa_score) < 0.6:
            severity = "high" if float(visa_row.visa_score) == 0.0 else "medium"
            warnings.append(
                ValidationWarning(
                    type="visa",
                    severity=severity,
                    message=f"Visa required: {str(visa_row.visa_type).replace('_', ' ').title()}",
                )
            )
    else:
        info["visa_type"] = "unknown"
        warnings.append(
            ValidationWarning(
                type="visa",
                severity="low",
                message="Visa requirements unknown — verify before booking.",
            )
        )

    # --- Season check ---
    season_row = db.execute(
        text(
            "SELECT season_score, avg_temp_c, avg_precipitation_mm, avg_humidity_pct "
            "FROM destination_seasonality "
            "WHERE destination_id = :did AND month = :month"
        ),
        {"did": dest_id, "month": request.travel_month},
    ).fetchone()

    if season_row:
        info["season_score"] = float(season_row.season_score)
        info["avg_temp_c"] = float(season_row.avg_temp_c)
        info["avg_precipitation_mm"] = float(season_row.avg_precipitation_mm)
        if season_row.avg_humidity_pct is not None:
            info["avg_humidity_pct"] = float(season_row.avg_humidity_pct)

        if float(season_row.season_score) < 0.4:
            reasons: list[str] = []
            t = season_row.avg_temp_c
            p = season_row.avg_precipitation_mm
            h = season_row.avg_humidity_pct
            if t is not None and float(t) > 35:
                reasons.append(f"extreme heat ({float(t):.0f}°C)")
            elif t is not None and float(t) < 0:
                reasons.append(f"freezing temperatures ({float(t):.0f}°C)")
            if p is not None and float(p) > 200:
                reasons.append(f"monsoon season ({float(p):.0f}mm/month)")
            if h is not None and float(h) > 85:
                reasons.append(f"very high humidity ({float(h):.0f}%)")
            if not reasons:
                reasons = (
                    [f"{float(t):.0f}°C, {float(p):.0f}mm precipitation"] if t and p else ["unfavourable conditions"]
                )
            warnings.append(
                ValidationWarning(
                    type="season",
                    severity="medium",
                    message=f"Poor travel month: {', '.join(reasons)}.",
                )
            )

    # --- Safety check ---
    safety_row = db.execute(
        text("SELECT safety_score FROM destination_safety WHERE destination_id = :did"),
        {"did": dest_id},
    ).fetchone()

    if safety_row:
        info["safety_score"] = float(safety_row.safety_score)
        if float(safety_row.safety_score) < 0.3:
            warnings.append(
                ValidationWarning(
                    type="safety",
                    severity="high",
                    message="Elevated safety risk. Check travel advisories before booking.",
                )
            )

    # --- Budget check (optional) ---
    if request.budget_per_day_usd is not None:
        costs_row = db.execute(
            text("SELECT avg_daily_cost_usd FROM destination_costs WHERE destination_id = :did"),
            {"did": dest_id},
        ).fetchone()

        if costs_row and costs_row.avg_daily_cost_usd:
            avg_daily = float(costs_row.avg_daily_cost_usd)
            info["avg_daily_cost_usd"] = avg_daily
            if request.budget_per_day_usd < avg_daily * 0.7:
                warnings.append(
                    ValidationWarning(
                        type="budget",
                        severity="medium",
                        message=(
                            f"Budget may be tight: avg daily cost is "
                            f"${avg_daily:.0f}/day, your budget is "
                            f"${request.budget_per_day_usd:.0f}/day."
                        ),
                    )
                )

    return ValidateTripResponse(
        destination_id=request.destination_id,
        warnings=warnings,
        info=info,
    )
