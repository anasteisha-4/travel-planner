"""Budget ML model training (Phase 6.5).

Architecture (formula + residual):
  1. Baseline = formula from budget.py (meals + transport + hotel_tier)
  2. Features: destination features (39-dim) + trip params
  3. Three LightGBM quantile regressors: p10, p50 (median), p90 on residuals
  4. Final prediction = baseline + residual_prediction
  5. MAPE evaluated on p50 vs actual

Usage (inside Docker):
    python scripts/train_budget_model.py [--holdout 0.2]
"""

import argparse
import io
import json
import logging
import math
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.budget_formula import (  # noqa: E402
    ACC_TIER_ENCODING,
    estimate_travel_cost,
    formula_baseline,
    haversine,
    seasonal_mult_from_json,
)
from app.services.feature_matrix import build_destination_feature_matrix, get_feature_columns  # noqa: E402

MODEL_SAVE_DIR = Path("/tmp/ml_models")

# ---- LightGBM shared params ----
LGBM_BASE = {
    "objective": "quantile",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "max_depth": 7,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "lambda_l1": 0.05,
    "lambda_l2": 0.1,
    "verbose": -1,
    "n_jobs": -1,
}
N_ROUNDS = 600
EARLY_STOPPING = 50


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_actuals(db: Session) -> pd.DataFrame:
    rows = db.execute(
        text(
            "SELECT tba.destination_id, tba.duration_days, tba.people_count, "
            "tba.travel_month, tba.accommodation_tier, tba.total_actual_usd, "
            "tba.travel_to_destination_usd, tba.origin_lat, tba.origin_lng, "
            "dc.avg_meal_cost_usd, dc.avg_transport_cost_usd, dc.avg_hotel_cost_usd, "
            "dc.avg_daily_cost_usd, dc.cost_index, dc.hostel_usd, dc.budget_usd, "
            "dc.mid_usd, dc.luxury_usd, dc.seasonal_multiplier, "
            "d.lat AS dest_lat, d.lng AS dest_lng "
            "FROM trip_budget_actuals tba "
            "JOIN destination_costs dc ON dc.destination_id = tba.destination_id "
            "JOIN destinations d ON d.id = tba.destination_id "
            "WHERE tba.total_actual_usd > 0"
        )
    ).fetchall()
    logger.info("Loaded %d budget actuals", len(rows))
    return pd.DataFrame([dict(r._mapping) for r in rows])


def _nullable_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


def compute_baselines(df: pd.DataFrame) -> np.ndarray:
    """Compute formula baseline for each row. Returns 1-D array."""
    baselines = []
    for _, row in df.iterrows():
        row_: Any = row
        seasonal = seasonal_mult_from_json(row_.get("seasonal_multiplier"), int(float(row_["travel_month"])))
        origin_lat = _nullable_float(row_.get("origin_lat"))
        origin_lng = _nullable_float(row_.get("origin_lng"))
        dest_lat = float(row_["dest_lat"]) if row_.get("dest_lat") is not None else 0.0
        dest_lng = float(row_["dest_lng"]) if row_.get("dest_lng") is not None else 0.0
        travel_cost = estimate_travel_cost(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            int(float(row_["people_count"])),
            int(float(row_["travel_month"])),
        )
        b = formula_baseline(
            avg_daily_cost=float(row_["avg_daily_cost_usd"]) if row_["avg_daily_cost_usd"] is not None else 80.0,
            avg_meal_cost=_nullable_float(row_.get("avg_meal_cost_usd")),
            avg_transport_cost=_nullable_float(row_.get("avg_transport_cost_usd")),
            avg_activity_cost=None,
            hostel_usd=_nullable_float(row_.get("hostel_usd")),
            budget_usd=_nullable_float(row_.get("budget_usd")),
            mid_usd=_nullable_float(row_.get("mid_usd")),
            luxury_usd=_nullable_float(row_.get("luxury_usd")),
            seasonal_mult=seasonal,
            duration_days=int(float(row_["duration_days"])),
            people_count=int(float(row_["people_count"])),
            accommodation_tier=str(row_["accommodation_tier"]),
            travel_to_destination=travel_cost,
        )
        baselines.append(b)
    return np.array(baselines, dtype=np.float64)


def build_features(df: pd.DataFrame, dest_df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    """Build feature matrix: trip params (9) + destination features (39) = 48 dims."""
    dest_idx = {str(row["destination_id"]): i for i, row in dest_df.iterrows()}

    X_rows = []
    for _, row in df.iterrows():
        row_: Any = row
        dest_id_str = str(row_["destination_id"])
        if dest_id_str in dest_idx:
            dest_row = dest_df.iloc[dest_idx[dest_id_str]]
            dest_vec = dest_row[feature_cols].values.astype(np.float32)
        else:
            dest_vec = np.zeros(len(feature_cols), dtype=np.float32)

        seasonal = seasonal_mult_from_json(row_.get("seasonal_multiplier"), int(float(row_["travel_month"])))

        season_col = f"season_{int(float(row_['travel_month'])):02d}"
        season_score = float(dest_df.iloc[dest_idx[dest_id_str]][season_col]) if dest_id_str in dest_idx else 0.65

        origin_lat = _nullable_float(row_.get("origin_lat"))
        origin_lng = _nullable_float(row_.get("origin_lng"))
        dest_lat = float(row_["dest_lat"]) if row_.get("dest_lat") is not None else 0.0
        dest_lng = float(row_["dest_lng"]) if row_.get("dest_lng") is not None else 0.0
        travel_cost = estimate_travel_cost(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            int(float(row_["people_count"])),
            int(float(row_["travel_month"])),
        )
        distance_km = haversine(origin_lat or 0.0, origin_lng or 0.0, dest_lat, dest_lng) if origin_lat else 0.0

        trip_vec = np.array(
            [
                float(row_["duration_days"]),
                math.log1p(float(row_["duration_days"])),
                float(row_["people_count"]),
                float(row_["travel_month"]) / 12.0,
                float(ACC_TIER_ENCODING.get(str(row_["accommodation_tier"]), 2)),
                seasonal,
                season_score,
                travel_cost,
                math.log1p(distance_km),
            ],
            dtype=np.float32,
        )

        X_rows.append(np.concatenate([trip_vec, dest_vec]))

    return np.stack(X_rows).astype(np.float32)


# ---------------------------------------------------------------------------
# Train / eval
# ---------------------------------------------------------------------------


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual > 1.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def train_quantile(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    alpha: float,
    feature_names: list[str],
) -> lgb.Booster:
    params = {**LGBM_BASE, "alpha": alpha}
    ds_train = lgb.Dataset(X_train, label=y_train, feature_name=feature_names, free_raw_data=False)
    ds_val = lgb.Dataset(X_val, label=y_val, reference=ds_train, free_raw_data=False)

    model = lgb.train(
        params,
        ds_train,
        num_boost_round=N_ROUNDS,
        valid_sets=[ds_val],
        callbacks=[
            lgb.log_evaluation(period=100),
            lgb.early_stopping(stopping_rounds=EARLY_STOPPING, verbose=False),
        ],
    )
    return model


def _sanitize_metrics(metrics: dict) -> dict:
    """Replace NaN/Inf with None so json.dumps produces valid JSON."""
    clean = {}
    for k, v in metrics.items():
        if isinstance(v, float) and (v != v or v == float("inf") or v == float("-inf")):
            clean[k] = None
        else:
            clean[k] = v
    return clean


def register_budget_model(db: Session, artifact: dict, metrics: dict, model_path: str) -> str:
    db.execute(text("UPDATE model_registry SET is_active = false WHERE model_type = 'budget'"))
    model_id = str(uuid.uuid4())

    buf = io.BytesIO()
    joblib.dump(artifact, buf)
    blob = buf.getvalue()
    logger.info("Budget model artifact: %.1f KB", len(blob) / 1024)

    db.execute(
        text(
            "INSERT INTO model_registry "
            "(id, name, version, model_type, is_active, metrics, model_path, model_blob, trained_at) "
            "VALUES (:id, 'budget', 'budget-v1', 'budget', true, cast(:metrics as jsonb), :path, :blob, :now)"
        ),
        {
            "id": model_id,
            "metrics": json.dumps(_sanitize_metrics(metrics)),
            "path": model_path,
            "blob": blob,
            "now": datetime.now(UTC),
        },
    )
    db.commit()
    return model_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(holdout: float = 0.20) -> None:
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_planner")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        count = db.execute(text("SELECT COUNT(*) FROM trip_budget_actuals")).scalar()
        if not count:
            logger.error("trip_budget_actuals is empty — run generate_synthetic_data.py first")
            sys.exit(1)
        logger.info("trip_budget_actuals: %d rows", count)

        logger.info("=== Phase 1: Destination feature matrix ===")
        dest_df = build_destination_feature_matrix(db)
        feature_cols = get_feature_columns()
        logger.info("Destinations: %d × %d features", len(dest_df), len(feature_cols))

        logger.info("=== Phase 2: Load budget actuals ===")
        df = load_actuals(db)

        logger.info("=== Phase 3: Compute formula baselines ===")
        baselines = compute_baselines(df)
        actuals = df["total_actual_usd"].values.astype(np.float64)
        residuals = actuals - baselines

        mape_formula = mape(actuals, baselines)
        logger.info("Formula baseline MAPE: %.2f%%", mape_formula)
        logger.info(
            "Residual stats: mean=%.2f  std=%.2f  p10=%.2f  p90=%.2f",
            residuals.mean(),
            residuals.std(),
            np.percentile(residuals, 10),
            np.percentile(residuals, 90),
        )

        logger.info("=== Phase 4: Build feature matrix ===")
        X = build_features(df, dest_df, feature_cols)
        n_feat = X.shape[1]
        logger.info("Feature matrix: %d × %d", len(X), n_feat)

        # Train/test split (random, budget data has no query structure)
        rng = np.random.default_rng(42)
        idx = rng.permutation(len(X))
        n_test = int(len(X) * holdout)
        test_idx = idx[:n_test]
        train_idx = idx[n_test:]

        X_train, X_test = X[train_idx], X[test_idx]
        resid_train, resid_test = residuals[train_idx], residuals[test_idx]
        actual_test = actuals[test_idx]
        baseline_test = baselines[test_idx]

        feature_names = [
            "trip_duration",
            "trip_log_duration",
            "trip_people",
            "trip_month_norm",
            "trip_acc_tier",
            "trip_seasonal",
            "trip_season_score",
            "trip_travel_cost",
            "trip_log_distance",
        ] + feature_cols
        logger.info("Train: %d  Test: %d", len(X_train), len(X_test))

        logger.info("=== Phase 5: Train quantile models ===")
        logger.info("--- p10 (alpha=0.10) ---")
        model_p10 = train_quantile(X_train, resid_train, X_test, resid_test, 0.10, feature_names)
        logger.info("--- p50 / median (alpha=0.50) ---")
        model_p50 = train_quantile(X_train, resid_train, X_test, resid_test, 0.50, feature_names)
        logger.info("--- p90 (alpha=0.90) ---")
        model_p90 = train_quantile(X_train, resid_train, X_test, resid_test, 0.90, feature_names)

        logger.info("=== Phase 6: Evaluate ===")
        pred_p10 = baseline_test + model_p10.predict(X_test)
        pred_p50 = baseline_test + model_p50.predict(X_test)
        pred_p90 = baseline_test + model_p90.predict(X_test)

        # Ensure p10 <= p50 <= p90 (quantile crossing fix)
        pred_p10 = np.minimum(pred_p10, pred_p50)
        pred_p90 = np.maximum(pred_p90, pred_p50)

        mape_ml = mape(actual_test, pred_p50)
        mape_improvement = mape_formula - mape_ml
        coverage = float(np.mean((actual_test >= pred_p10) & (actual_test <= pred_p90)) * 100)

        logger.info("MAPE (formula baseline): %.2f%%", mape_formula)
        logger.info("MAPE (ML p50):           %.2f%%", mape_ml)
        logger.info("Improvement:             %.2f pp", mape_improvement)
        logger.info("P10–P90 interval coverage: %.1f%% (target ~80%%)", coverage)

        if mape_ml > 25.0:
            logger.warning("MAPE %.2f%% > 25%% threshold", mape_ml)
        else:
            logger.info("MAPE target met ✓")

        # Feature importance (p50 model)
        imp = sorted(
            zip(feature_names, model_p50.feature_importance("gain"), strict=False),
            key=lambda x: -x[1],
        )[:15]
        logger.info("Top features (p50 gain): %s", [(n, int(v)) for n, v in imp])

        logger.info("=== Phase 7: Save model ===")
        MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        model_path = str(MODEL_SAVE_DIR / "budget_v1.joblib")

        artifact = {
            "model_p10": model_p10,
            "model_p50": model_p50,
            "model_p90": model_p90,
            "feature_cols": feature_cols,
            "feature_names": feature_names,
            "n_trip_features": 9,
        }
        joblib.dump(artifact, model_path)

        metrics = {
            "mape_formula": round(mape_formula, 4),
            "mape_ml_p50": round(mape_ml, 4),
            "mape_improvement_pp": round(mape_improvement, 4),
            "p10_p90_coverage_pct": round(coverage, 2),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": n_feat,
            "best_iter_p50": int(model_p50.best_iteration),
        }

        model_id = register_budget_model(db, artifact, metrics, model_path)
        logger.info("Registered budget model: id=%s", model_id)
        logger.info("=== Done: MAPE=%.2f%%  coverage=%.1f%% ===", mape_ml, coverage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", type=float, default=0.20)
    args = parser.parse_args()
    main(holdout=args.holdout)
