"""Train in-trip remaining-spend quantile model.

The current product has sparse real completed trips, so this training job
builds checkpoint rows from synthetic `trip_budget_actuals`. It is intentionally
registered as a separate model (`in-trip-budget-v1`) from the pre-trip budget
model and remains replaceable by real completed-trip checkpoints later.
"""

import argparse
import io
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.in_trip_budget_scorer import FEATURE_NAMES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_SAVE_DIR = Path("/tmp/ml_models")
CHECKPOINT_RATIOS = (0.0, 0.25, 0.5, 0.75)
LGBM_BASE = {
    "objective": "quantile",
    "learning_rate": 0.04,
    "num_leaves": 31,
    "max_depth": 6,
    "min_data_in_leaf": 30,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 5,
    "lambda_l1": 0.05,
    "lambda_l2": 0.15,
    "verbose": -1,
    "n_jobs": -1,
}
N_ROUNDS = 450
EARLY_STOPPING = 40


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return default if parsed != parsed else parsed


def load_budget_rows(db: Session) -> pd.DataFrame:
    rows = db.execute(
        text(
            "SELECT tba.destination_id, tba.duration_days, tba.people_count, "
            "tba.travel_month, tba.accommodation_tier, tba.total_actual_usd, "
            "tba.travel_to_destination_usd, dc.avg_daily_cost_usd, dc.hostel_usd, "
            "dc.budget_usd, dc.mid_usd, dc.luxury_usd "
            "FROM trip_budget_actuals tba "
            "JOIN destination_costs dc ON dc.destination_id = tba.destination_id "
            "WHERE tba.total_actual_usd > 0"
        )
    ).fetchall()
    return pd.DataFrame([dict(row._mapping) for row in rows])


def _category_actuals(row: Any) -> dict[str, float]:
    total = _safe_float(row["total_actual_usd"])
    travel = max(0.0, _safe_float(row.get("travel_to_destination_usd")))
    duration = max(1.0, _safe_float(row["duration_days"], 1.0))
    people = max(1.0, _safe_float(row["people_count"], 1.0))
    avg_daily = max(40.0, _safe_float(row.get("avg_daily_cost_usd"), 80.0))
    tier = str(row.get("accommodation_tier") or "mid")
    tier_col = {"hostel": "hostel_usd", "budget": "budget_usd", "mid": "mid_usd", "luxury": "luxury_usd"}.get(
        tier, "mid_usd"
    )
    nightly = _safe_float(row.get(tier_col), avg_daily * 0.65)
    housing = min(total * 0.55, nightly * np.ceil(people / 2.0) * duration)
    food = min(total * 0.35, avg_daily * 0.34 * people * duration)
    local_transport = min(total * 0.22, avg_daily * 0.12 * people * duration)
    entertainment = min(total * 0.22, avg_daily * 0.10 * people * duration)
    shopping = total * 0.05
    known = travel + housing + food + local_transport + entertainment + shopping
    other = max(0.0, total - known)
    return {
        "housing": housing,
        "food": food,
        "transport": travel + local_transport,
        "entertainment": entertainment,
        "shopping": shopping,
        "other": other,
    }


def build_checkpoint_rows(df: pd.DataFrame, seed: int = 42) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    features = []
    baselines = []
    remaining_actuals = []
    trip_group_ids = []

    for row_idx, row in df.iterrows():
        row_: Any = row
        duration = int(max(1, _safe_float(row_["duration_days"], 1)))
        people = int(max(1, _safe_float(row_["people_count"], 1)))
        category_actual = _category_actuals(row_)
        total_actual = sum(category_actual.values())
        travel_actual = min(category_actual["transport"], _safe_float(row_.get("travel_to_destination_usd")))

        for ratio in CHECKPOINT_RATIOS:
            elapsed = max(1, min(duration, int(round(duration * ratio)) or 1))
            remaining = max(0, duration - elapsed)
            progress = elapsed / duration

            fixed_paid = category_actual["housing"] * min(1.0, 0.65 + progress * 0.45)
            travel_paid = travel_actual if progress >= 0.05 else 0.0
            food_spent = category_actual["food"] * progress * rng.normal(1.0, 0.08)
            local_transport_spent = max(
                0.0, (category_actual["transport"] - travel_actual) * progress * rng.normal(1.0, 0.10)
            )
            entertainment_spent = category_actual["entertainment"] * max(0.0, progress - 0.05) * rng.normal(1.0, 0.14)
            shopping_spent = category_actual["shopping"] * max(0.0, progress - 0.15) * rng.normal(1.0, 0.18)
            other_spent = category_actual["other"] * progress * rng.normal(1.0, 0.16)

            spent_by_category = {
                "housing": max(0.0, fixed_paid),
                "food": max(0.0, food_spent),
                "transport": max(0.0, travel_paid + local_transport_spent),
                "entertainment": max(0.0, entertainment_spent),
                "shopping": max(0.0, shopping_spent),
                "other": max(0.0, other_spent),
            }
            current_spent = sum(spent_by_category.values())
            locked_fixed = spent_by_category["housing"] + travel_paid
            recurring_spent = spent_by_category["food"] + local_transport_spent + other_spent
            optional_spent = spent_by_category["entertainment"] + spent_by_category["shopping"]
            daily_recurring_rate = recurring_spent / elapsed

            remaining_poi = max(0.0, remaining * rng.normal(3.2, 0.5))
            paid_poi = max(0.0, remaining_poi * rng.uniform(0.12, 0.32))
            food_poi = max(0.0, remaining * rng.normal(1.0, 0.2))
            itinerary_fee = paid_poi * rng.normal(14.0, 4.0)
            pretrip_total_mid = total_actual * rng.normal(1.0, 0.08)
            baseline_remaining = max(
                0.0,
                (category_actual["housing"] - spent_by_category["housing"])
                + (category_actual["transport"] - spent_by_category["transport"])
                + daily_recurring_rate * remaining * 0.45
                + (category_actual["food"] + category_actual["entertainment"] + category_actual["shopping"])
                * (remaining / duration)
                * 0.55
                + itinerary_fee * 0.35,
            )
            remaining_actual = max(0.0, total_actual - current_spent)

            features.append(
                [
                    float(duration),
                    float(elapsed),
                    float(remaining),
                    progress,
                    float(people),
                    np.log1p(max(0.0, pretrip_total_mid)),
                    np.log1p(max(0.0, pretrip_total_mid)),
                    np.log1p(current_spent),
                    np.log1p(locked_fixed),
                    np.log1p(recurring_spent),
                    np.log1p(optional_spent),
                    np.log1p(daily_recurring_rate),
                    np.log1p(spent_by_category["food"]),
                    np.log1p(spent_by_category["transport"]),
                    np.log1p(spent_by_category["housing"]),
                    np.log1p(spent_by_category["entertainment"]),
                    np.log1p(spent_by_category["shopping"]),
                    np.log1p(spent_by_category["other"]),
                    float(remaining),
                    remaining_poi,
                    paid_poi,
                    food_poi,
                    np.log1p(max(0.0, itinerary_fee)),
                    remaining_poi / max(remaining, 1),
                ]
            )
            baselines.append(baseline_remaining)
            remaining_actuals.append(remaining_actual)
            trip_group_ids.append(row_idx)

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(baselines, dtype=np.float64),
        np.asarray(remaining_actuals, dtype=np.float64),
        np.asarray(trip_group_ids, dtype=np.int64),
    )


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual > 1.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _train_quantile(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    alpha: float,
) -> lgb.Booster:
    params = {**LGBM_BASE, "alpha": alpha}
    ds_train = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_NAMES, free_raw_data=False)
    ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_train, free_raw_data=False)
    return lgb.train(
        params,
        ds_train,
        num_boost_round=N_ROUNDS,
        valid_sets=[ds_val],
        callbacks=[lgb.log_evaluation(period=100), lgb.early_stopping(EARLY_STOPPING, verbose=False)],
    )


def _sanitize_metrics(metrics: dict) -> dict:
    return {
        key: None if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}) else value
        for key, value in metrics.items()
    }


def register_model(db: Session, artifact: dict, metrics: dict, model_path: str) -> str:
    db.execute(text("UPDATE model_registry SET is_active = false WHERE model_type = 'in_trip_budget'"))
    model_id = str(uuid.uuid4())
    buf = io.BytesIO()
    joblib.dump(artifact, buf)
    db.execute(
        text(
            "INSERT INTO model_registry "
            "(id, name, version, model_type, is_active, metrics, model_path, model_blob, trained_at) "
            "VALUES (:id, 'in_trip_budget', 'in-trip-budget-v1', 'in_trip_budget', true, "
            "cast(:metrics as jsonb), :path, :blob, :now)"
        ),
        {
            "id": model_id,
            "metrics": json.dumps(_sanitize_metrics(metrics)),
            "path": model_path,
            "blob": buf.getvalue(),
            "now": datetime.now(UTC),
        },
    )
    db.commit()
    return model_id


def main(holdout: float = 0.2) -> None:
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        df = load_budget_rows(db)
        if df.empty:
            raise SystemExit("trip_budget_actuals is empty")
        X, baselines, actual_remaining, group_ids = build_checkpoint_rows(df)
        residuals = actual_remaining - baselines
        unique_groups = np.unique(group_ids)
        rng = np.random.default_rng(42)
        rng.shuffle(unique_groups)
        n_test_groups = max(1, int(len(unique_groups) * holdout))
        test_groups = set(unique_groups[:n_test_groups])
        test_mask = np.array([gid in test_groups for gid in group_ids])
        train_mask = ~test_mask

        X_train, X_test = X[train_mask], X[test_mask]
        residual_train, residual_test = residuals[train_mask], residuals[test_mask]
        actual_test, baseline_test = actual_remaining[test_mask], baselines[test_mask]

        logger.info("Checkpoint rows: %d train=%d test=%d", len(X), len(X_train), len(X_test))
        model_p10 = _train_quantile(X_train, residual_train, X_test, residual_test, 0.10)
        model_p50 = _train_quantile(X_train, residual_train, X_test, residual_test, 0.50)
        model_p90 = _train_quantile(X_train, residual_train, X_test, residual_test, 0.90)

        pred_p10 = baseline_test + model_p10.predict(X_test)
        pred_p50 = baseline_test + model_p50.predict(X_test)
        pred_p90 = baseline_test + model_p90.predict(X_test)
        pred_p10 = np.minimum(pred_p10, pred_p50)
        pred_p90 = np.maximum(pred_p90, pred_p50)

        mape_baseline = _mape(actual_test, baseline_test)
        mape_ml = _mape(actual_test, pred_p50)
        coverage = float(np.mean((actual_test >= pred_p10) & (actual_test <= pred_p90)) * 100)
        logger.info("Baseline MAPE %.2f%%; ML MAPE %.2f%%; coverage %.2f%%", mape_baseline, mape_ml, coverage)

        MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        model_path = str(MODEL_SAVE_DIR / "in_trip_budget_v1.joblib")
        artifact = {
            "model_p10": model_p10,
            "model_p50": model_p50,
            "model_p90": model_p90,
            "feature_names": FEATURE_NAMES,
            "version": "in-trip-budget-v1",
        }
        joblib.dump(artifact, model_path)
        metrics = {
            "mape_baseline": round(mape_baseline, 4),
            "mape_ml_p50": round(mape_ml, 4),
            "mape_improvement_pp": round(mape_baseline - mape_ml, 4),
            "p10_p90_coverage_pct": round(coverage, 2),
            "n_checkpoint_rows": int(len(X)),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "n_features": int(X.shape[1]),
            "split": "by_synthetic_trip",
        }
        model_id = register_model(db, artifact, metrics, model_path)
        logger.info("Registered in-trip budget model: %s", model_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", type=float, default=0.2)
    args = parser.parse_args()
    main(args.holdout)
