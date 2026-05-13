import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.services.analytics_events import emit_ml_quality_event
from app.services.currency import convert_usd, normalize_currency

router = APIRouter()


class ValidateTripRequest(BaseModel):
    destination_id: uuid.UUID
    citizenship_code: str = "RU"
    travel_month: int = Field(..., ge=1, le=12)
    budget_per_day_usd: float | None = None
    display_currency: str | None = None
    duration_days: int | None = Field(default=None, ge=1, le=365)
    risk_tolerance: int | None = Field(default=None, ge=1, le=5)
    language_code: str | None = None
    preferred_language: str | None = None


class ValidationWarning(BaseModel):
    type: str
    severity: str  # "high" | "medium" | "low"
    message: str


class ValidateTripResponse(BaseModel):
    destination_id: uuid.UUID
    warnings: list[ValidationWarning]
    info: dict


def _language_column(language: str | None) -> tuple[str, str] | None:
    if not language:
        return None
    normalized = language.strip().lower()
    if normalized in {"ru", "rus", "russian", "русский"}:
        return "russian_speaking_score", "Russian"
    if normalized in {"en", "eng", "english", "английский"}:
        return "english_speaking_score", "English"
    return None


def _safety_severity(safety_score: float, risk_tolerance: int | None) -> str | None:
    tolerance = risk_tolerance or 3
    high_threshold = 0.45 if tolerance <= 2 else 0.30 if tolerance == 3 else 0.20
    medium_threshold = 0.62 if tolerance <= 2 else 0.45 if tolerance == 3 else 0.35
    if safety_score < high_threshold:
        return "high"
    if safety_score < medium_threshold:
        return "medium"
    return None


def _script_difficulty_score(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int | float)):
        return float(value)
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    label_scores = {"easy": 0.0, "medium": 0.5, "hard": 1.0}
    if normalized in label_scores:
        return label_scores[normalized]
    try:
        return float(normalized)
    except ValueError:
        return None


@router.post("/validate", response_model=ValidateTripResponse)
def validate_trip(
    request: ValidateTripRequest,
    authorization: str | None = Header(default=None),
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
            if request.duration_days is not None and request.duration_days > int(visa_row.max_stay_days):
                warnings.append(
                    ValidationWarning(
                        type="visa",
                        severity="high",
                        message=(
                            f"Trip is longer than allowed stay: {request.duration_days} days "
                            f"vs {int(visa_row.max_stay_days)} days."
                        ),
                    )
                )
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
        safety_score = float(safety_row.safety_score)
        safety_severity = _safety_severity(safety_score, request.risk_tolerance)
        info["safety_score"] = safety_score
        if request.risk_tolerance is not None:
            info["risk_tolerance"] = request.risk_tolerance
        if safety_severity:
            warnings.append(
                ValidationWarning(
                    type="safety",
                    severity=safety_severity,
                    message=("Elevated safety risk for your risk tolerance. Check travel advisories before booking."),
                )
            )

    # --- Language comfort check (optional) ---
    language = request.preferred_language or request.language_code
    language_lookup = _language_column(language)
    if language_lookup is not None:
        column, label = language_lookup
        language_row = db.execute(
            text(
                f"SELECT {column} AS comfort_score, script_difficulty "
                "FROM destination_language_accessibility WHERE destination_id = :did"
            ),
            {"did": dest_id},
        ).fetchone()
        if language_row:
            comfort_score = float(language_row.comfort_score or 0.0)
            info["language_code"] = language
            info["language_comfort_score"] = comfort_score
            script_difficulty = _script_difficulty_score(language_row.script_difficulty)
            if script_difficulty is not None:
                info["script_difficulty"] = script_difficulty
            if comfort_score < 0.35:
                warnings.append(
                    ValidationWarning(
                        type="language",
                        severity="low",
                        message=f"{label} language comfort may be limited for this destination.",
                    )
                )

    # --- Budget check (optional) ---
    if request.budget_per_day_usd is not None:
        display_currency = normalize_currency(request.display_currency)
        costs_row = db.execute(
            text("SELECT avg_daily_cost_usd FROM destination_costs WHERE destination_id = :did"),
            {"did": dest_id},
        ).fetchone()

        if costs_row and costs_row.avg_daily_cost_usd:
            avg_daily = float(costs_row.avg_daily_cost_usd)
            avg_daily_display = convert_usd(avg_daily, display_currency)
            budget_per_day_display = convert_usd(request.budget_per_day_usd, display_currency)
            info["avg_daily_cost_usd"] = avg_daily
            info["avg_daily_cost"] = avg_daily_display
            info["budget_per_day"] = budget_per_day_display
            info["display_currency"] = display_currency
            if request.budget_per_day_usd < avg_daily * 0.7:
                avg_text = (
                    f"{avg_daily_display:.0f} {display_currency}/day"
                    if avg_daily_display is not None
                    else f"${avg_daily:.0f}/day"
                )
                budget_text = (
                    f"{budget_per_day_display:.0f} {display_currency}/day"
                    if budget_per_day_display is not None
                    else f"${request.budget_per_day_usd:.0f}/day"
                )
                warnings.append(
                    ValidationWarning(
                        type="budget",
                        severity="medium",
                        message=(f"Budget may be tight: avg daily cost is {avg_text}, your budget is {budget_text}."),
                    )
                )

    response = ValidateTripResponse(
        destination_id=request.destination_id,
        warnings=warnings,
        info=info,
    )
    emit_ml_quality_event(
        "validation_result_served",
        {
            "destination_id": str(request.destination_id),
            "travel_month": request.travel_month,
            "warnings_count": len(warnings),
            "warning_types": [warning.type for warning in warnings],
            "warning_severities": [warning.severity for warning in warnings],
            "visa_state": info.get("visa_type"),
            "season_score": info.get("season_score"),
            "safety_score": info.get("safety_score"),
            "language_comfort_score": info.get("language_comfort_score"),
        },
        entity_type="destination",
        entity_id=request.destination_id,
        authorization=authorization,
    )
    return response
