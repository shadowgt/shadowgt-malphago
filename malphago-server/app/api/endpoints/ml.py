"""ML 모델 관리 API 엔드포인트"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/status")
async def get_ml_status():
    """현재 ML 모델 상태를 반환한다."""
    from app.ml.trainer import load_model, MODEL_DIR

    status = {"models": {}}
    for name in ["lightgbm", "xgboost"]:
        model, meta = load_model(name)
        if model is not None:
            status["models"][name] = {
                "available": True,
                "trained_at": meta.get("trained_at"),
                "n_samples": meta.get("n_samples"),
                "n_features": meta.get("n_features"),
                "feature_importance": meta.get("feature_importance", {}),
            }
        else:
            status["models"][name] = {"available": False}

    status["model_dir"] = str(MODEL_DIR)
    return status


@router.get("/predict/{race_id}")
async def predict_race_ml_endpoint(
    race_id: int,
    model: str = "lightgbm",
    db: AsyncSession = Depends(get_db),
):
    """ML 모델로 경주를 예측한다."""
    if model not in ("lightgbm", "xgboost"):
        raise HTTPException(400, "model must be 'lightgbm' or 'xgboost'")

    from app.ml.predictor import predict_race_ml
    results = await predict_race_ml(db, race_id, model_name=model)
    if not results:
        raise HTTPException(404, "Race not found or no entries")
    return results


@router.post("/reload")
async def reload_ml_model(model: str = "lightgbm"):
    """ML 모델 캐시를 갱신한다."""
    if model not in ("lightgbm", "xgboost"):
        raise HTTPException(400, "model must be 'lightgbm' or 'xgboost'")

    from app.ml.predictor import reload_model
    success = reload_model(model)
    return {"reloaded": success, "model": model}


@router.post("/retrain")
async def trigger_retrain(db: AsyncSession = Depends(get_db)):
    """모델 재학습 파이프라인을 수동 트리거한다."""
    from app.ml.auto_retrain import retrain_pipeline
    result = await retrain_pipeline(db)
    return result


@router.get("/report/weekly")
async def get_weekly_report(
    weeks: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """주간 모델 성능 리포트를 생성한다."""
    from app.ml.weekly_report import generate_weekly_report
    report = await generate_weekly_report(db, weeks=weeks)
    return report


@router.get("/report/trend")
async def get_accuracy_trend_endpoint(
    weeks: int = 8,
    db: AsyncSession = Depends(get_db),
):
    """최근 N주간 정확도 추이를 반환한다."""
    from app.ml.weekly_report import get_accuracy_trend
    trend = await get_accuracy_trend(db, weeks=weeks)
    return trend
