"""ML 모델 기반 예측기

학습된 LightGBM/XGBoost 모델을 사용하여 경주 결과를 예측한다.
기존 가중 선형 모델(prediction.py)과 공존하며,
모델이 없을 경우 자동으로 기존 모델로 폴백한다.
"""

import json
import logging
from dataclasses import asdict

import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.prediction import Prediction
from app.services.prediction import predict_entry, PredictionFactors
from app.ml.trainer import load_model
from app.ml.feature_extractor import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

# Cached model
_cached_model = None
_cached_meta = None


def get_ml_model(model_name: str = "lightgbm"):
    """캐시된 ML 모델을 반환한다."""
    global _cached_model, _cached_meta
    if _cached_model is None:
        _cached_model, _cached_meta = load_model(model_name)
    return _cached_model, _cached_meta


def reload_model(model_name: str = "lightgbm"):
    """모델 캐시를 갱신한다."""
    global _cached_model, _cached_meta
    _cached_model, _cached_meta = load_model(model_name)
    return _cached_model is not None


async def predict_race_ml(
    session: AsyncSession,
    race_id: int,
    model_name: str = "lightgbm",
) -> list[dict]:
    """ML 모델로 경주 예측을 실행한다.

    기존 prediction.py의 15개 요인을 피처로 활용하되,
    가중합 대신 ML 모델이 확률을 출력한다.

    Args:
        session: DB session
        race_id: 경주 ID
        model_name: 사용할 모델명

    Returns:
        예측 결과 리스트 (entry_id, score, rank, factors)
    """
    model, meta = get_ml_model(model_name)
    if model is None:
        logger.warning("ML model not found, falling back to weighted linear")
        from app.services.prediction import predict_race
        return await predict_race(session, race_id)

    race = await session.get(Race, race_id)
    if not race:
        logger.error(f"Race not found: {race_id}")
        return []

    entries_q = select(RaceEntry).where(RaceEntry.race_id == race_id)
    entries_result = await session.execute(entries_q)
    entries = entries_result.scalars().all()

    if not entries:
        return []

    feature_cols = meta.get("feature_cols", FEATURE_COLUMNS)

    scores = []
    for entry in entries:
        try:
            _, factors = await predict_entry(session, entry, race)
        except Exception as e:
            logger.warning(f"Factor calc failed for entry {entry.id}: {e}")
            continue

        # Build feature vector
        factors_dict = asdict(factors)
        feature_row = {}
        for col in feature_cols:
            if col in factors_dict:
                feature_row[col] = factors_dict[col]
            elif col == "odds_win":
                feature_row[col] = float(entry.odds_win) if entry.odds_win else np.nan
            elif col == "odds_place":
                feature_row[col] = float(entry.odds_place) if entry.odds_place else np.nan
            elif col == "horse_weight":
                feature_row[col] = entry.horse_weight or np.nan
            elif col == "horse_weight_change":
                feature_row[col] = entry.horse_weight_change or np.nan
            elif col == "race_interval":
                feature_row[col] = entry.race_interval or np.nan
            elif col == "horse_number":
                feature_row[col] = entry.horse_number or np.nan
            elif col == "total_entries":
                feature_row[col] = race.total_entries or np.nan
            elif col == "rating":
                feature_row[col] = entry.rating or np.nan
            elif col == "distance":
                feature_row[col] = race.distance or np.nan
            elif col == "favor_ranking":
                feature_row[col] = entry.favor_ranking or np.nan
            else:
                feature_row[col] = np.nan

        import pandas as pd
        X = pd.DataFrame([feature_row])[feature_cols]
        # NaN fill with 0 for prediction (median not available at inference)
        X = X.fillna(0)

        prob = model.predict_proba(X)[0][1]  # P(top3)
        ml_score = round(prob * 100, 2)

        scores.append({
            "entry": entry,
            "total_score": ml_score,
            "factors": factors_dict,
            "ml_probability": prob,
        })

    # Sort by ML score
    scores.sort(key=lambda x: x["total_score"], reverse=True)

    model_version = f"ml_{model_name}_{meta.get('trained_at', 'unknown')}"

    results = []
    for rank, item in enumerate(scores, 1):
        entry = item["entry"]
        factors_dict = item["factors"]
        factors_dict["ml_probability"] = item["ml_probability"]

        # Update or create Prediction record
        existing_q = select(Prediction).where(
            and_(
                Prediction.race_id == race_id,
                Prediction.entry_id == entry.id,
                Prediction.is_override == False,
            )
        )
        existing_result = await session.execute(existing_q)
        existing = existing_result.scalar_one_or_none()

        confidence = _calc_ml_confidence(item["ml_probability"], scores)

        if existing:
            existing.total_score = item["total_score"]
            existing.predicted_rank = rank
            existing.confidence = confidence
            existing.factors_json = json.dumps(factors_dict, ensure_ascii=False)
            existing.model_version = model_version
        else:
            pred = Prediction(
                race_id=race_id,
                entry_id=entry.id,
                total_score=item["total_score"],
                predicted_rank=rank,
                confidence=confidence,
                factors_json=json.dumps(factors_dict, ensure_ascii=False),
                model_version=model_version,
            )
            session.add(pred)

        results.append({
            "entry_id": entry.id,
            "horse_number": entry.horse_number,
            "total_score": item["total_score"],
            "predicted_rank": rank,
            "ml_probability": round(item["ml_probability"], 4),
            "factors": factors_dict,
        })

    await session.commit()
    logger.info(f"ML predicted race {race_id}: {len(results)} entries ({model_version})")
    return results


def _calc_ml_confidence(prob: float, all_scores: list[dict]) -> float:
    """ML 확률 기반 신뢰도 계산"""
    if not all_scores:
        return 50.0

    probs = sorted([s["ml_probability"] for s in all_scores], reverse=True)
    if len(probs) >= 2:
        gap = probs[0] - probs[1]
        return min(50 + gap * 200, 95.0)
    return 60.0
