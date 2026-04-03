"""ML 모델 학습기

LightGBM과 XGBoost 모델을 학습하고 평가한다.
시계열 교차검증 (Leave-One-Date-Out) 방식으로 과적합을 방지한다.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    log_loss,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "ml_models"


def get_models() -> dict:
    """학습할 모델 목록을 반환한다."""
    import lightgbm as lgb
    import xgboost as xgb

    return {
        "lightgbm": lgb.LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=10,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            verbose=-1,
        ),
        "xgboost": xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            eval_metric="logloss",
            verbosity=0,
        ),
    }


def time_series_cv(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "is_top3",
    model_name: str = "lightgbm",
    min_train_dates: int = 10,
) -> dict:
    """시계열 교차검증 (Leave-One-Date-Out)

    각 경주일을 테스트셋으로 사용하고, 나머지를 학습셋으로 사용한다.
    미래 데이터 누출을 방지하기 위해 테스트 날짜 이전 데이터만 학습에 사용한다.

    Args:
        df: 전체 데이터셋 (race_date 컬럼 필요)
        feature_cols: 피처 컬럼 리스트
        target_col: 타겟 컬럼
        model_name: 사용할 모델 ("lightgbm" or "xgboost")
        min_train_dates: 최소 학습 날짜 수

    Returns:
        교차검증 결과 dict
    """
    models = get_models()
    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}")

    dates = sorted(df["race_date"].unique())
    logger.info(f"TSCV: {len(dates)} unique dates, model={model_name}")

    date_results = []

    for i, test_date in enumerate(dates):
        # 학습: 테스트 날짜 이전 데이터만 사용 (미래 누출 방지)
        train_mask = df["race_date"] < test_date
        test_mask = df["race_date"] == test_date

        train_df = df[train_mask]
        test_df = df[test_mask]

        # 최소 학습 데이터 확보
        train_dates = train_df["race_date"].nunique()
        if train_dates < min_train_dates:
            continue

        X_train = train_df[feature_cols].copy()
        y_train = train_df[target_col].copy()
        X_test = test_df[feature_cols].copy()
        y_test = test_df[target_col].copy()

        # NaN 처리
        for col in feature_cols:
            median_val = X_train[col].median()
            X_train[col] = X_train[col].fillna(median_val)
            X_test[col] = X_test[col].fillna(median_val)

        if len(y_test) < 3 or y_test.nunique() < 2:
            continue

        model = get_models()[model_name]

        try:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]

            result = {
                "date": test_date,
                "n_train": len(X_train),
                "n_test": len(X_test),
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, zero_division=0),
                "recall": recall_score(y_test, y_pred, zero_division=0),
                "f1": f1_score(y_test, y_pred, zero_division=0),
                "auc": roc_auc_score(y_test, y_prob),
                "log_loss": log_loss(y_test, y_prob),
            }
            date_results.append(result)
        except Exception as e:
            logger.warning(f"TSCV failed for {test_date}: {e}")
            continue

        if (i + 1) % 20 == 0:
            logger.info(f"TSCV progress: {i + 1}/{len(dates)}")

    if not date_results:
        return {"error": "No valid folds"}

    results_df = pd.DataFrame(date_results)

    summary = {
        "model": model_name,
        "n_folds": len(date_results),
        "n_dates_total": len(dates),
        "metrics": {
            "accuracy": {
                "mean": float(results_df["accuracy"].mean()),
                "std": float(results_df["accuracy"].std()),
                "min": float(results_df["accuracy"].min()),
                "max": float(results_df["accuracy"].max()),
            },
            "f1": {
                "mean": float(results_df["f1"].mean()),
                "std": float(results_df["f1"].std()),
            },
            "auc": {
                "mean": float(results_df["auc"].mean()),
                "std": float(results_df["auc"].std()),
            },
            "precision": {
                "mean": float(results_df["precision"].mean()),
                "std": float(results_df["precision"].std()),
            },
            "recall": {
                "mean": float(results_df["recall"].mean()),
                "std": float(results_df["recall"].std()),
            },
        },
        "per_date": date_results,
    }

    logger.info(
        f"TSCV {model_name}: accuracy={summary['metrics']['accuracy']['mean']:.3f}"
        f"±{summary['metrics']['accuracy']['std']:.3f}, "
        f"AUC={summary['metrics']['auc']['mean']:.3f}"
    )

    return summary


def train_final_model(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "is_top3",
    model_name: str = "lightgbm",
) -> tuple:
    """전체 데이터로 최종 모델을 학습하고 저장한다.

    Returns:
        (model, model_path, feature_importance)
    """
    models = get_models()
    model = models[model_name]

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # NaN 처리
    for col in feature_cols:
        X[col] = X[col].fillna(X[col].median())

    model.fit(X, y)

    # Feature importance
    if hasattr(model, "feature_importances_"):
        importance = dict(zip(feature_cols, model.feature_importances_.tolist()))
    else:
        importance = {}

    # Save model
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"{model_name}_{timestamp}.joblib"
    metadata_path = MODEL_DIR / f"{model_name}_{timestamp}_meta.joblib"

    joblib.dump(model, model_path)
    joblib.dump(
        {
            "model_name": model_name,
            "feature_cols": feature_cols,
            "target_col": target_col,
            "n_samples": len(X),
            "n_features": len(feature_cols),
            "trained_at": timestamp,
            "feature_importance": importance,
        },
        metadata_path,
    )

    # Symlink to latest
    latest_path = MODEL_DIR / f"{model_name}_latest.joblib"
    latest_meta = MODEL_DIR / f"{model_name}_latest_meta.joblib"
    if latest_path.exists():
        latest_path.unlink()
    if latest_meta.exists():
        latest_meta.unlink()

    # Use copy on Windows (symlinks need admin)
    import shutil
    shutil.copy2(model_path, latest_path)
    shutil.copy2(metadata_path, latest_meta)

    logger.info(f"Model saved: {model_path}")
    return model, str(model_path), importance


def load_model(model_name: str = "lightgbm") -> tuple:
    """저장된 모델을 로드한다.

    Returns:
        (model, metadata) or (None, None) if not found
    """
    model_path = MODEL_DIR / f"{model_name}_latest.joblib"
    meta_path = MODEL_DIR / f"{model_name}_latest_meta.joblib"

    if not model_path.exists():
        logger.warning(f"Model not found: {model_path}")
        return None, None

    model = joblib.load(model_path)
    metadata = joblib.load(meta_path)
    logger.info(f"Model loaded: {model_name}, trained={metadata.get('trained_at')}")
    return model, metadata


def compare_models(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "is_top3",
) -> dict:
    """LightGBM과 XGBoost를 비교한다.

    Returns:
        {"lightgbm": cv_result, "xgboost": cv_result, "best": model_name}
    """
    results = {}
    for name in ["lightgbm", "xgboost"]:
        logger.info(f"Evaluating {name}...")
        cv = time_series_cv(df, feature_cols, target_col, model_name=name)
        results[name] = cv

    # AUC 기준으로 best 선택
    best = max(
        results.keys(),
        key=lambda k: results[k].get("metrics", {}).get("auc", {}).get("mean", 0),
    )
    results["best"] = best

    logger.info(f"Best model: {best}")
    return results
