"""In-trip budget monitoring.

The endpoint starts from the pre-trip prediction, then switches to a transparent
tempo baseline once the user records actual expenses. Planning and one-time
expenses are locked as paid amounts; other expenses are projected with a
trimmed mean over the full trip duration. A bounded ML residual can calibrate
the tempo baseline when an active in-trip model is available.
"""

import io
import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Any

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.budget import BudgetMonitorRequest
from app.services.currency import SUPPORTED_CURRENCY_RATES, normalize_currency

logger = logging.getLogger(__name__)

# Baseline constants are used only when a pre-trip prediction or enough real
# expenses are missing. They encode conservative UX assumptions rather than
# learned parameters; the active LightGBM model then predicts residuals.
FALLBACK_DAILY_BY_TIER_USD = {
    "hostel": 65.0,
    "budget": 85.0,
    "mid": 125.0,
    "luxury": 260.0,
}
FALLBACK_BREAKDOWN_SHARES = {
    "accommodation": 0.35,
    "meals": 0.30,
    "transport": 0.15,
    "activities": 0.10,
    "travel_to_destination": 0.10,
}
SHOPPING_REMAINING_TOTAL_SHARE = 0.03
OTHER_REMAINING_TOTAL_SHARE = 0.025
UNCERTAINTY_BASE = 0.18
UNCERTAINTY_REMAINING_DAYS_WEIGHT = 0.22
UNCERTAINTY_NO_PRICE_EVIDENCE_ADDON = 0.10
TRIMMED_MEAN_MIN_SAMPLES = 5
TRIMMED_MEAN_FRACTION = 0.20
ML_RESIDUAL_MAX_RELATIVE = 0.20
ML_RESIDUAL_ABSOLUTE_FLOOR_USD = 100.0

FEATURE_NAMES = [
    "duration_days",
    "elapsed_days",
    "remaining_days",
    "progress_ratio",
    "people_count",
    "cost_anchor_usd_log",
    "pretrip_total_mid_usd_log",
    "current_spent_usd_log",
    "locked_fixed_usd_log",
    "recurring_spent_usd_log",
    "optional_activity_spent_usd_log",
    "daily_recurring_rate_usd_log",
    "food_spent_usd_log",
    "transport_spent_usd_log",
    "housing_spent_usd_log",
    "entertainment_spent_usd_log",
    "shopping_spent_usd_log",
    "other_spent_usd_log",
    "itinerary_remaining_days",
    "itinerary_remaining_poi",
    "itinerary_paid_poi",
    "itinerary_food_poi",
    "itinerary_fee_usd_log",
    "poi_per_remaining_day",
]


@dataclass(frozen=True)
class ClassifiedExpense:
    category: str
    kind: str
    amount_usd: float
    expense_date: date | None = None
    description: str | None = None


@dataclass(frozen=True)
class InTripBaseline:
    current_spent_usd: float
    planning_spent_usd: float
    locked_fixed_usd: float
    recurring_spent_usd: float
    optional_activity_spent_usd: float
    remaining_mid_usd: float
    remaining_min_usd: float
    remaining_max_usd: float
    category_remaining_usd: dict[str, float]
    category_spent_usd: dict[str, float]
    category_kind: dict[str, str]
    assumptions: dict[str, Any]
    feature_vector: np.ndarray


def convert_to_usd(amount: float, currency: str) -> float:
    rate = SUPPORTED_CURRENCY_RATES.get(normalize_currency(currency), 1.0)
    return amount / rate


def convert_from_usd(amount_usd: float, currency: str) -> float:
    rate = SUPPORTED_CURRENCY_RATES.get(normalize_currency(currency), 1.0)
    return round(amount_usd * rate, 2)


def trip_days(start: date, end: date, as_of: date | None) -> tuple[int, int, int]:
    duration = max(1, (end - start).days + 1)
    today = as_of or date.today()
    if today <= start:
        return duration, 0, duration
    active_day = min(max(today, start), end)
    elapsed = max(1, (active_day - start).days + 1)
    remaining = max(0, duration - elapsed)
    return duration, elapsed, remaining


def classify_expense(
    category: str,
    description: str | None,
    expense_date: date | None,
    start: date,
    end: date,
    is_one_time: bool = False,
) -> str:
    if expense_date is not None and (expense_date < start or expense_date > end):
        return "planning_once"
    if is_one_time:
        return "fixed_once"
    return "recurring_daily"


def classify_expenses(request: BudgetMonitorRequest) -> list[ClassifiedExpense]:
    target_currency = normalize_currency(request.currency)
    classified: list[ClassifiedExpense] = []
    for expense in request.expenses:
        amount = expense.converted_amount if expense.converted_amount is not None else expense.amount
        currency = target_currency if expense.converted_amount is not None else expense.currency
        classified.append(
            ClassifiedExpense(
                category=expense.category,
                kind=classify_expense(
                    expense.category,
                    expense.description,
                    expense.expense_date,
                    request.start_date,
                    request.end_date,
                    expense.is_one_time,
                ),
                amount_usd=convert_to_usd(float(amount), currency),
                expense_date=expense.expense_date,
                description=expense.description,
            )
        )
    return classified


def _is_destination_travel_paid(expense: ClassifiedExpense) -> bool:
    return expense.category.lower() == "travel_to_destination"


def _trimmed_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) < TRIMMED_MEAN_MIN_SAMPLES:
        sample = ordered
    else:
        trim_count = int(len(ordered) * TRIMMED_MEAN_FRACTION)
        if trim_count == 0 and len(ordered) >= TRIMMED_MEAN_MIN_SAMPLES:
            trim_count = 1
        sample = ordered[trim_count : len(ordered) - trim_count] if trim_count else ordered
        if not sample:
            sample = ordered
    return sum(sample) / len(sample)


def _pretrip_category_total_usd(category: str, pretrip_breakdown: dict[str, float]) -> float:
    normalized = category.lower()
    if normalized == "housing":
        return pretrip_breakdown.get("housing", 0.0)
    if normalized == "food":
        return pretrip_breakdown.get("food", 0.0)
    if normalized == "transport":
        return pretrip_breakdown.get("transport", 0.0)
    if normalized == "travel_to_destination":
        return pretrip_breakdown.get("travel_to_destination", 0.0)
    if normalized == "entertainment":
        return pretrip_breakdown.get("entertainment", 0.0)
    if normalized in {"shopping", "other"}:
        return pretrip_breakdown.get(normalized, 0.0)
    return 0.0


def _clamp_ml_residual(residual: float, baseline_remaining: float) -> float:
    limit = max(baseline_remaining * ML_RESIDUAL_MAX_RELATIVE, ML_RESIDUAL_ABSOLUTE_FLOOR_USD)
    return min(max(residual, -limit), limit)


def _breakdown_usd(request: BudgetMonitorRequest, key: str) -> float:
    prediction = request.pre_trip_prediction
    if prediction is None:
        return 0.0
    value = float(prediction.breakdown.get(key, 0.0) or 0.0)
    return convert_to_usd(value, request.currency)


def _fallback_total_mid_usd(request: BudgetMonitorRequest, category_spent: dict[str, float]) -> float:
    current = sum(category_spent.values())
    duration, _, _ = trip_days(request.start_date, request.end_date, request.as_of_date)
    daily = FALLBACK_DAILY_BY_TIER_USD.get(request.accommodation_tier, FALLBACK_DAILY_BY_TIER_USD["mid"])
    formula_default = daily * max(request.people_count, 1) * max(duration, 1)
    return max(current, formula_default)


def _pretrip_total_mid_usd(request: BudgetMonitorRequest, category_spent: dict[str, float]) -> float:
    if request.pre_trip_prediction and request.pre_trip_prediction.total_mid:
        return convert_to_usd(float(request.pre_trip_prediction.total_mid), request.currency)
    return _fallback_total_mid_usd(request, category_spent)


def _feature_vector(
    request: BudgetMonitorRequest,
    duration: int,
    elapsed: int,
    remaining: int,
    current_spent: float,
    locked_fixed: float,
    recurring_spent: float,
    optional_activity_spent: float,
    category_spent: dict[str, float],
    pretrip_total_mid: float,
    daily_recurring_rate: float,
) -> np.ndarray:
    itinerary = request.itinerary_summary
    remaining_itinerary_days = float(itinerary.remaining_days_count if itinerary else remaining)
    remaining_poi = float(itinerary.remaining_poi_count if itinerary else 0)
    paid_poi = float(itinerary.remaining_paid_poi_count if itinerary else 0)
    food_poi = float(itinerary.remaining_food_poi_count if itinerary else 0)
    fees = convert_to_usd(float(itinerary.remaining_estimated_entrance_fees if itinerary else 0), request.currency)
    poi_per_day = remaining_poi / max(remaining_itinerary_days, 1.0)

    values = [
        float(duration),
        float(elapsed),
        float(remaining),
        elapsed / max(duration, 1),
        float(request.people_count),
        math.log1p(pretrip_total_mid),
        math.log1p(pretrip_total_mid),
        math.log1p(current_spent),
        math.log1p(locked_fixed),
        math.log1p(recurring_spent),
        math.log1p(optional_activity_spent),
        math.log1p(daily_recurring_rate),
        math.log1p(category_spent.get("food", 0.0)),
        math.log1p(category_spent.get("transport", 0.0)),
        math.log1p(category_spent.get("housing", 0.0)),
        math.log1p(category_spent.get("entertainment", 0.0)),
        math.log1p(category_spent.get("shopping", 0.0)),
        math.log1p(category_spent.get("other", 0.0)),
        remaining_itinerary_days,
        remaining_poi,
        paid_poi,
        food_poi,
        math.log1p(fees),
        poi_per_day,
    ]
    return np.array(values, dtype=np.float32)


def compute_baseline(request: BudgetMonitorRequest) -> InTripBaseline:
    duration, elapsed, remaining = trip_days(request.start_date, request.end_date, request.as_of_date)
    expenses = classify_expenses(request)

    raw_category_spent: dict[str, float] = {}
    for expense in expenses:
        raw_category_spent[expense.category] = raw_category_spent.get(expense.category, 0.0) + expense.amount_usd

    pretrip_total_mid = _pretrip_total_mid_usd(request, raw_category_spent)
    pretrip_accommodation = _breakdown_usd(request, "accommodation")
    pretrip_meals = _breakdown_usd(request, "meals")
    pretrip_transport = _breakdown_usd(request, "transport")
    pretrip_activities = _breakdown_usd(request, "activities")
    pretrip_travel = _breakdown_usd(request, "travel_to_destination")

    if request.pre_trip_prediction is None:
        pretrip_accommodation = pretrip_total_mid * FALLBACK_BREAKDOWN_SHARES["accommodation"]
        pretrip_meals = pretrip_total_mid * FALLBACK_BREAKDOWN_SHARES["meals"]
        pretrip_transport = pretrip_total_mid * FALLBACK_BREAKDOWN_SHARES["transport"]
        pretrip_activities = pretrip_total_mid * FALLBACK_BREAKDOWN_SHARES["activities"]
        pretrip_travel = pretrip_total_mid * FALLBACK_BREAKDOWN_SHARES["travel_to_destination"]

    category_spent: dict[str, float] = {}
    category_kind: dict[str, str] = {}
    planning_spent = locked_fixed = recurring_spent = optional_activity_spent = 0.0
    for expense in expenses:
        kind = expense.kind
        is_destination_travel = _is_destination_travel_paid(expense)
        if is_destination_travel and kind != "planning_once":
            kind = "fixed_once"
        category = "travel_to_destination" if is_destination_travel else expense.category
        category_spent[category] = category_spent.get(category, 0.0) + expense.amount_usd
        if category_kind.get(category) != "fixed_once":
            category_kind[category] = kind
        if kind == "planning_once":
            planning_spent += expense.amount_usd
        elif kind == "fixed_once":
            locked_fixed += expense.amount_usd
        elif kind == "optional_activity":
            optional_activity_spent += expense.amount_usd
        else:
            recurring_spent += expense.amount_usd

    current_spent = planning_spent + locked_fixed + recurring_spent + optional_activity_spent

    destination_transport_paid = sum(expense.amount_usd for expense in expenses if _is_destination_travel_paid(expense))
    destination_travel_recorded = destination_transport_paid > 0

    itinerary = request.itinerary_summary
    itinerary_fee_remaining = convert_to_usd(
        float(itinerary.remaining_estimated_entrance_fees if itinerary else 0.0),
        request.currency,
    )
    evidence_fee_remaining = convert_to_usd(
        float(itinerary.remaining_evidence_backed_entrance_fees if itinerary else 0.0),
        request.currency,
    )
    recurring_expected_components = pretrip_meals + pretrip_transport + pretrip_activities
    daily_recurring_expected = recurring_expected_components / max(duration, 1)
    observed_daily_recurring = recurring_spent / max(elapsed, 1)

    if request.pre_trip_prediction is not None and current_spent == 0 and elapsed == 0:
        category_remaining = {
            "housing": max(0.0, pretrip_accommodation),
            "travel_to_destination": max(0.0, pretrip_travel),
            "transport": max(0.0, pretrip_transport),
            "food": max(0.0, pretrip_meals),
            "entertainment": max(0.0, pretrip_activities),
        }
        categorized_total = sum(category_remaining.values())
        residual = max(0.0, pretrip_total_mid - categorized_total)
        if residual > 0:
            category_remaining["other"] = residual
        remaining_mid = pretrip_total_mid
        remaining_min = (
            convert_to_usd(float(request.pre_trip_prediction.total_min), request.currency)
            if request.pre_trip_prediction.total_min is not None
            else max(0.0, remaining_mid * (1 - UNCERTAINTY_BASE))
        )
        remaining_max = (
            convert_to_usd(float(request.pre_trip_prediction.total_max), request.currency)
            if request.pre_trip_prediction.total_max is not None
            else max(remaining_mid, remaining_mid * (1 + UNCERTAINTY_BASE))
        )
        assumptions = {
            "duration_days": duration,
            "elapsed_days": elapsed,
            "remaining_days": remaining,
            "expense_classification": {
                "planning_once": round(planning_spent, 2),
                "fixed_once": round(locked_fixed, 2),
                "recurring_daily": round(recurring_spent, 2),
                "optional_activity": round(optional_activity_spent, 2),
            },
            "pretrip_total_mid_usd": round(pretrip_total_mid, 2),
            "daily_recurring_expected_usd": round(daily_recurring_expected, 2),
            "observed_daily_recurring_usd": round(observed_daily_recurring, 2),
            "itinerary_fee_remaining_usd": round(itinerary_fee_remaining, 2),
            "itinerary_evidence_fee_remaining_usd": round(evidence_fee_remaining, 2),
            "itinerary_evidence_backed_price_count": itinerary.evidence_backed_price_count if itinerary else 0,
            "itinerary_candidate_poi_price_count": itinerary.candidate_poi_price_count if itinerary else 0,
            "itinerary_price_estimation_used": itinerary.price_estimation_used if itinerary else False,
            "destination_transport_paid_usd": round(destination_transport_paid, 2),
            "pretrip_anchor_applied": True,
        }
        feature_vector = _feature_vector(
            request,
            duration,
            elapsed,
            remaining,
            current_spent,
            locked_fixed,
            recurring_spent,
            optional_activity_spent,
            category_spent,
            pretrip_total_mid,
            daily_recurring_expected,
        )
        return InTripBaseline(
            current_spent_usd=current_spent,
            planning_spent_usd=planning_spent,
            locked_fixed_usd=locked_fixed,
            recurring_spent_usd=recurring_spent,
            optional_activity_spent_usd=optional_activity_spent,
            remaining_mid_usd=remaining_mid,
            remaining_min_usd=remaining_min,
            remaining_max_usd=remaining_max,
            category_remaining_usd=category_remaining,
            category_spent_usd=category_spent,
            category_kind=category_kind,
            assumptions=assumptions,
            feature_vector=feature_vector,
        )

    pretrip_breakdown = {
        "housing": pretrip_accommodation,
        "food": pretrip_meals,
        "transport": pretrip_transport,
        "entertainment": pretrip_activities,
        "travel_to_destination": pretrip_travel,
        "shopping": pretrip_total_mid * SHOPPING_REMAINING_TOTAL_SHARE,
        "other": pretrip_total_mid * OTHER_REMAINING_TOTAL_SHARE,
    }
    remaining_progress_ratio = remaining / max(duration, 1)

    recurring_amounts_by_category: dict[str, list[float]] = {}
    for expense in expenses:
        if _is_destination_travel_paid(expense):
            continue
        if expense.kind in {"planning_once", "fixed_once"}:
            continue
        recurring_amounts_by_category.setdefault(expense.category, []).append(expense.amount_usd)

    projected_recurring_total_by_category: dict[str, float] = {}
    trimmed_mean_by_category: dict[str, float] = {}
    for category, amounts in recurring_amounts_by_category.items():
        trimmed_mean = _trimmed_mean(amounts)
        trimmed_mean_by_category[category] = trimmed_mean
        projected_recurring_total_by_category[category] = max(
            category_spent.get(category, 0.0),
            trimmed_mean * duration,
        )

    category_remaining: dict[str, float] = {}
    projection_categories = set(pretrip_breakdown) | set(category_spent) | set(recurring_amounts_by_category)
    for category in projection_categories:
        spent = category_spent.get(category, 0.0)
        if category == "travel_to_destination" and destination_travel_recorded:
            category_remaining[category] = 0.0
            category_kind[category] = "fixed_once"
            continue
        if category in projected_recurring_total_by_category:
            projected_total = projected_recurring_total_by_category[category]
            category_remaining[category] = max(0.0, projected_total - spent)
            category_kind[category] = "recurring_daily"
            continue

        planned_total = _pretrip_category_total_usd(category, pretrip_breakdown)
        planned_remaining = max(0.0, planned_total - spent) * remaining_progress_ratio
        category_remaining[category] = planned_remaining

    if "entertainment" not in recurring_amounts_by_category:
        category_remaining["entertainment"] = max(category_remaining.get("entertainment", 0.0), itinerary_fee_remaining)

    remaining_mid = max(0.0, sum(category_remaining.values()))
    projected_final_mid = current_spent + remaining_mid

    uncertainty = (
        UNCERTAINTY_BASE
        + UNCERTAINTY_REMAINING_DAYS_WEIGHT * (remaining / max(duration, 1))
        + (UNCERTAINTY_NO_PRICE_EVIDENCE_ADDON if itinerary_fee_remaining == 0 else 0.0)
    )
    remaining_min = max(0.0, remaining_mid * (1 - uncertainty))
    remaining_max = max(remaining_mid, remaining_mid * (1 + uncertainty))

    assumptions = {
        "duration_days": duration,
        "elapsed_days": elapsed,
        "remaining_days": remaining,
        "expense_classification": {
            "planning_once": round(planning_spent, 2),
            "fixed_once": round(locked_fixed, 2),
            "recurring_daily": round(recurring_spent, 2),
            "optional_activity": round(optional_activity_spent, 2),
        },
        "pretrip_total_mid_usd": round(pretrip_total_mid, 2),
        "daily_recurring_expected_usd": round(daily_recurring_expected, 2),
        "observed_daily_recurring_usd": round(observed_daily_recurring, 2),
        "itinerary_fee_remaining_usd": round(itinerary_fee_remaining, 2),
        "itinerary_evidence_fee_remaining_usd": round(evidence_fee_remaining, 2),
        "itinerary_evidence_backed_price_count": itinerary.evidence_backed_price_count if itinerary else 0,
        "itinerary_candidate_poi_price_count": itinerary.candidate_poi_price_count if itinerary else 0,
        "itinerary_price_estimation_used": itinerary.price_estimation_used if itinerary else False,
        "destination_transport_paid_usd": round(destination_transport_paid, 2),
        "recurring_projection_method": "trimmed_mean_per_expense_times_trip_duration",
        "recurring_trim_fraction": TRIMMED_MEAN_FRACTION,
        "recurring_trimmed_mean_by_category_usd": {
            category: round(value, 2) for category, value in sorted(trimmed_mean_by_category.items())
        },
        "recurring_projected_total_by_category_usd": {
            category: round(value, 2) for category, value in sorted(projected_recurring_total_by_category.items())
        },
        "projected_final_mid_usd_formula": round(projected_final_mid, 2),
        "ml_residual_allowed": recurring_spent > 0,
        "ml_residual_role": "bounded_calibration_of_trimmed_mean_tempo",
    }

    feature_vector = _feature_vector(
        request,
        duration,
        elapsed,
        remaining,
        current_spent,
        locked_fixed,
        recurring_spent,
        optional_activity_spent,
        category_spent,
        pretrip_total_mid,
        observed_daily_recurring,
    )

    return InTripBaseline(
        current_spent_usd=current_spent,
        planning_spent_usd=planning_spent,
        locked_fixed_usd=locked_fixed,
        recurring_spent_usd=recurring_spent,
        optional_activity_spent_usd=optional_activity_spent,
        remaining_mid_usd=remaining_mid,
        remaining_min_usd=remaining_min,
        remaining_max_usd=remaining_max,
        category_remaining_usd=category_remaining,
        category_spent_usd=category_spent,
        category_kind=category_kind,
        assumptions=assumptions,
        feature_vector=feature_vector,
    )


class InTripBudgetScorer:
    def __init__(self, model_id: str, blob: bytes | None = None, model_path: str | None = None) -> None:
        self._model_id = model_id
        self._blob = blob
        self._model_path = model_path
        self._artifact: dict | None = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._artifact is not None
        self._loaded = True
        try:
            if self._blob:
                self._artifact = joblib.load(io.BytesIO(self._blob))
            elif self._model_path and __import__("os").path.exists(self._model_path):
                self._artifact = joblib.load(self._model_path)
        except Exception as exc:
            logger.warning("Failed to load in-trip budget model: %s", exc)
        return self._artifact is not None

    def predict(self, baseline: InTripBaseline) -> tuple[float, float, float] | None:
        if not self._ensure_loaded() or self._artifact is None:
            return None
        X = baseline.feature_vector.reshape(1, -1)
        try:
            residual_p10 = float(self._artifact["model_p10"].predict(X)[0])
            residual_p50 = float(self._artifact["model_p50"].predict(X)[0])
            residual_p90 = float(self._artifact["model_p90"].predict(X)[0])
        except Exception as exc:
            logger.warning("Failed to run in-trip budget model: %s", exc)
            return None
        residual_p10 = _clamp_ml_residual(residual_p10, baseline.remaining_mid_usd)
        residual_p50 = _clamp_ml_residual(residual_p50, baseline.remaining_mid_usd)
        residual_p90 = _clamp_ml_residual(residual_p90, baseline.remaining_mid_usd)
        p10 = max(0.0, baseline.remaining_mid_usd + residual_p10)
        p50 = max(0.0, baseline.remaining_mid_usd + residual_p50)
        p90 = max(0.0, baseline.remaining_mid_usd + residual_p90)
        return min(p10, p50), p50, max(p90, p50)


_scorer_cache: InTripBudgetScorer | None = None


def get_in_trip_budget_scorer(db: Session) -> InTripBudgetScorer | None:
    global _scorer_cache
    row = db.execute(
        text(
            "SELECT id, model_path, model_blob FROM model_registry "
            "WHERE model_type = 'in_trip_budget' AND is_active = true "
            "ORDER BY trained_at DESC LIMIT 1"
        )
    ).fetchone()
    if row is None:
        return None
    model_id = str(row.id)
    if _scorer_cache is not None and _scorer_cache._model_id == model_id:
        return _scorer_cache
    _scorer_cache = InTripBudgetScorer(
        model_id=model_id,
        blob=bytes(row.model_blob) if row.model_blob else None,
        model_path=row.model_path,
    )
    return _scorer_cache
