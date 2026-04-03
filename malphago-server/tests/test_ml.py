"""ML 파이프라인 테스트"""

import json
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.ml.feature_extractor import FEATURE_COLUMNS, TARGET_COL, prepare_xy
from app.ml.trainer import time_series_cv, train_final_model, compare_models, MODEL_DIR


def _make_sample_df(n_dates=10, entries_per_date=8):
    """테스트용 샘플 DataFrame 생성"""
    rows = []
    for d in range(n_dates):
        date = f"2025-01-{d + 1:02d}"
        race_id = d + 1
        for e in range(entries_per_date):
            row = {col: np.random.uniform(20, 80) for col in FEATURE_COLUMNS}
            row["race_id"] = race_id
            row["entry_id"] = d * entries_per_date + e
            row["race_date"] = date
            row["track_id"] = 1
            row["ranking"] = e + 1
            row["is_top3"] = 1 if e < 3 else 0
            row["is_win"] = 1 if e == 0 else 0
            rows.append(row)
    return pd.DataFrame(rows)


class TestFeatureExtractor:
    def test_feature_columns_defined(self):
        assert len(FEATURE_COLUMNS) >= 15
        assert "horse_win_rate" in FEATURE_COLUMNS
        assert "odds_win" in FEATURE_COLUMNS

    def test_target_col(self):
        assert TARGET_COL == "is_top3"

    def test_prepare_xy(self):
        df = _make_sample_df()
        X, y = prepare_xy(df)
        assert len(X) == len(y)
        assert len(X.columns) > 0
        assert y.dtype in [np.int64, np.float64, int]
        # No NaN after preparation
        assert X.isna().sum().sum() == 0

    def test_prepare_xy_handles_nan(self):
        df = _make_sample_df()
        # Inject NaN
        df.loc[0, "odds_win"] = np.nan
        df.loc[1, "horse_weight"] = np.nan
        X, y = prepare_xy(df)
        assert X.isna().sum().sum() == 0


class TestTrainer:
    def test_time_series_cv_lightgbm(self):
        df = _make_sample_df(n_dates=15, entries_per_date=10)
        feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        result = time_series_cv(
            df, feature_cols, model_name="lightgbm", min_train_dates=5
        )
        assert "metrics" in result
        assert result["n_folds"] > 0
        assert 0 <= result["metrics"]["accuracy"]["mean"] <= 1
        assert 0 <= result["metrics"]["auc"]["mean"] <= 1

    def test_time_series_cv_xgboost(self):
        df = _make_sample_df(n_dates=15, entries_per_date=10)
        feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        result = time_series_cv(
            df, feature_cols, model_name="xgboost", min_train_dates=5
        )
        assert "metrics" in result
        assert result["n_folds"] > 0

    def test_train_final_model(self, tmp_path):
        df = _make_sample_df()
        feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]

        with patch("app.ml.trainer.MODEL_DIR", tmp_path):
            model, path, importance = train_final_model(
                df, feature_cols, model_name="lightgbm"
            )
        assert model is not None
        assert Path(path).exists()
        assert len(importance) > 0

    def test_compare_models(self):
        df = _make_sample_df(n_dates=15, entries_per_date=10)
        feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        results = compare_models(df, feature_cols)
        assert "lightgbm" in results
        assert "xgboost" in results
        assert results["best"] in ("lightgbm", "xgboost")

    def test_invalid_model_name(self):
        df = _make_sample_df()
        feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        with pytest.raises(ValueError, match="Unknown model"):
            time_series_cv(df, feature_cols, model_name="invalid")


class TestMLAPI:
    @pytest.fixture
    def client(self):
        from app.main import app
        from httpx import AsyncClient, ASGITransport
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_ml_status(self, client):
        async with client as c:
            resp = await c.get("/api/ml/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "lightgbm" in data["models"]

    @pytest.mark.asyncio
    async def test_ml_reload(self, client):
        async with client as c:
            resp = await c.post("/api/ml/reload?model=lightgbm")
        assert resp.status_code == 200
        data = resp.json()
        assert "reloaded" in data

    @pytest.mark.asyncio
    async def test_ml_predict_invalid_model(self, client):
        async with client as c:
            resp = await c.get("/api/ml/predict/1?model=invalid")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_ml_reload_invalid_model(self, client):
        async with client as c:
            resp = await c.post("/api/ml/reload?model=invalid")
        assert resp.status_code == 400
