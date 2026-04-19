"""Validate trip parameters: visa, season, safety warnings."""

from sqlalchemy.orm import Session


def validate_trip_params(
    db: Session,
    destination_id: str,
    citizenship_code: str,
    travel_month: int,
) -> dict:
    from app.models import DestinationSafety, DestinationSeasonality, VisaRule

    warnings = []
    info = {}

    # Visa check
    visa_rule = (
        db.query(VisaRule)
        .filter(
            VisaRule.destination_id == destination_id,
            VisaRule.citizenship_code == citizenship_code.upper(),
        )
        .first()
    )
    if visa_rule:
        info["visa_type"] = visa_rule.visa_type
        info["visa_score"] = visa_rule.visa_score
        if visa_rule.visa_score < 0.6:
            warnings.append(
                {
                    "type": "visa",
                    "severity": "high" if visa_rule.visa_score == 0.0 else "medium",
                    "message": f"Visa required: {visa_rule.visa_type.replace('_', ' ').title()}",
                }
            )
    else:
        info["visa_type"] = "unknown"
        warnings.append(
            {
                "type": "visa",
                "severity": "low",
                "message": "Visa requirements unknown, verify before travel.",
            }
        )

    # Season check
    season = (
        db.query(DestinationSeasonality)
        .filter(
            DestinationSeasonality.destination_id == destination_id,
            DestinationSeasonality.month == travel_month,
        )
        .first()
    )
    if season:
        info["season_score"] = season.season_score
        info["avg_temp_c"] = season.avg_temp_c
        info["avg_precipitation_mm"] = season.avg_precipitation_mm
        info["avg_humidity_pct"] = season.avg_humidity_pct
        if season.season_score < 0.4:
            reasons = []
            t = season.avg_temp_c
            p = season.avg_precipitation_mm
            h = season.avg_humidity_pct
            if t is not None and t > 35:
                reasons.append(f"сильная жара ({t:.0f}°C)")
            elif t is not None and t < 0:
                reasons.append(f"мороз ({t:.0f}°C)")
            if p is not None and p > 200:
                reasons.append(f"сезон дождей ({p:.0f}мм/мес)")
            if h is not None and h > 85:
                reasons.append(f"очень высокая влажность ({h:.0f}%)")
            if not reasons:
                # Fallback: show raw numbers if no specific threshold triggered
                parts = []
                if t is not None:
                    parts.append(f"{t:.0f}°C")
                if p is not None:
                    parts.append(f"{p:.0f}мм осадков")
                reasons = parts or ["неблагоприятные условия"]
            warnings.append(
                {
                    "type": "season",
                    "severity": "medium",
                    "message": f"Неудачный месяц для поездки: {', '.join(reasons)}.",
                    "reasons": reasons,
                }
            )

    # Safety check
    safety = (
        db.query(DestinationSafety)
        .filter(DestinationSafety.destination_id == destination_id)
        .first()
    )
    if safety:
        info["safety_score"] = safety.safety_score
        if safety.safety_score < 0.3:
            warnings.append(
                {
                    "type": "safety",
                    "severity": "high",
                    "message": "Elevated safety risk. Check travel advisories before booking.",
                }
            )

    return {"warnings": warnings, "info": info, "destination_id": destination_id}
