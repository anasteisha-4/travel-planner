"""In-trip budget monitoring with ML residual fallback.

The endpoint uses deterministic decomposition as a baseline and optionally
adds residual LightGBM quantile models trained from synthetic checkpoint rows.
"""

import io
import logging
import math
import re
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

FIXED_KEYWORDS = re.compile(
    r"\b(flight|airfare|airline|avia|plane|train|rail|ferry|ticket|booking|reservation|hotel|visa|insurance)\b"
    r"|авиа|самолет|самол[её]т|перел[её]т|рейс|поезд|жд|билет\w*|брон\w*|отель|гостиниц\w*|виза|страхов\w*",
    re.IGNORECASE,
)

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
    if today < start:
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
    normalized = category.lower()
    text = f"{category} {description or ''}"
    if expense_date is not None and (expense_date < start or expense_date > end):
        return "planning_once"
    if is_one_time or FIXED_KEYWORDS.search(text):
        return "fixed_once"
    if normalized == "housing":
        return "fixed_once"
    if normalized in {"food", "transport", "other"}:
        return "recurring_daily"
    if normalized in {"entertainment", "shopping"}:
        return "optional_activity"
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


def _is_destination_transport_paid(
    expense: ClassifiedExpense, pretrip_travel_usd: float, pretrip_total_mid: float
) -> bool:
    if expense.category.lower() != "transport":
        return False
    if expense.kind not in {"planning_once", "fixed_once"}:
        return False
    text = f"{expense.category} {expense.description or ''}"
    large_transport_threshold = max(pretrip_travel_usd * 0.35, pretrip_total_mid * 0.12, 120.0)
    return bool(FIXED_KEYWORDS.search(text)) or expense.amount_usd >= large_transport_threshold


def _breakdown_usd(request: BudgetMonitorRequest, key: str) -> float:
    prediction = request.pre_trip_prediction
    if prediction is None:
        return 0.0
    value = float(prediction.breakdown.get(key, 0.0) or 0.0)
    return convert_to_usd(value, request.currency)


def _fallback_total_mid_usd(request: BudgetMonitorRequest, category_spent: dict[str, float]) -> float:
    current = sum(category_spent.values())
    duration, _, _ = trip_days(request.start_date, request.end_date, request.as_of_date)
    tier_daily = {
        "hostel": 65.0,
        "budget": 85.0,
        "mid": 125.0,
        "luxury": 260.0,
    }
    daily = tier_daily.get(request.accommodation_tier, tier_daily["mid"])
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

    category_spent: dict[str, float] = {}
    category_kind: dict[str, str] = {}
    planning_spent = locked_fixed = recurring_spent = optional_activity_spent = 0.0
    for expense in expenses:
        category_spent[expense.category] = category_spent.get(expense.category, 0.0) + expense.amount_usd
        category_kind.setdefault(expense.category, expense.kind)
        if expense.kind == "planning_once":
            planning_spent += expense.amount_usd
        elif expense.kind == "fixed_once":
            locked_fixed += expense.amount_usd
        elif expense.kind == "optional_activity":
            optional_activity_spent += expense.amount_usd
        else:
            recurring_spent += expense.amount_usd

    current_spent = planning_spent + locked_fixed + recurring_spent + optional_activity_spent
    pretrip_total_mid = _pretrip_total_mid_usd(request, category_spent)
    pretrip_accommodation = _breakdown_usd(request, "accommodation")
    pretrip_meals = _breakdown_usd(request, "meals")
    pretrip_transport = _breakdown_usd(request, "transport")
    pretrip_activities = _breakdown_usd(request, "activities")
    pretrip_travel = _breakdown_usd(request, "travel_to_destination")

    if request.pre_trip_prediction is None:
        pretrip_accommodation = pretrip_total_mid * 0.35
        pretrip_meals = pretrip_total_mid * 0.30
        pretrip_transport = pretrip_total_mid * 0.15
        pretrip_activities = pretrip_total_mid * 0.10
        pretrip_travel = pretrip_total_mid * 0.10

    destination_transport_paid = sum(
        expense.amount_usd
        for expense in expenses
        if _is_destination_transport_paid(expense, pretrip_travel, pretrip_total_mid)
    )

    recurring_expected_components = pretrip_meals + pretrip_transport + pretrip_activities
    daily_recurring_expected = recurring_expected_components / max(duration, 1)
    observed_daily_recurring = recurring_spent / max(elapsed, 1)
    blended_daily = observed_daily_recurring * min(0.65, elapsed / max(duration, 1)) + daily_recurring_expected * (
        1 - min(0.65, elapsed / max(duration, 1))
    )
    recurring_total_expected = max(recurring_expected_components, 1.0)
    food_share = pretrip_meals / recurring_total_expected
    transport_share = pretrip_transport / recurring_total_expected
    activities_share = pretrip_activities / recurring_total_expected
    blended_recurring_remaining = max(0.0, blended_daily * remaining)

    housing_spent = category_spent.get("housing", 0.0)
    accommodation_remaining = max(0.0, pretrip_accommodation - housing_spent)
    travel_remaining = max(0.0, pretrip_travel - destination_transport_paid)

    itinerary = request.itinerary_summary
    itinerary_fee_remaining = convert_to_usd(
        float(itinerary.remaining_estimated_entrance_fees if itinerary else 0.0),
        request.currency,
    )
    activity_remaining = max(
        itinerary_fee_remaining,
        (pretrip_activities / max(duration, 1)) * remaining * 0.65,
    )

    category_remaining = {
        "housing": accommodation_remaining,
        "transport": max(0.0, travel_remaining + blended_recurring_remaining * transport_share),
        "food": max(0.0, blended_recurring_remaining * food_share),
        "entertainment": max(activity_remaining, blended_recurring_remaining * activities_share),
        "shopping": max(0.0, pretrip_total_mid * 0.03 * (remaining / max(duration, 1))),
        "other": max(0.0, pretrip_total_mid * 0.025 * (remaining / max(duration, 1))),
    }
    remaining_mid = sum(category_remaining.values())
    remaining_mid = max(0.0, remaining_mid)
    uncertainty = 0.18 + 0.22 * (remaining / max(duration, 1)) + (0.10 if itinerary_fee_remaining == 0 else 0.0)
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
        "destination_transport_paid_usd": round(destination_transport_paid, 2),
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
