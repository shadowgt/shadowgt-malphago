from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.prediction import Prediction
from app.services.prediction import predict_race

router = APIRouter()


@router.get("/race/{race_id}")
async def get_race_predictions(race_id: int, db: AsyncSession = Depends(get_db)):
    """경주 예측 결과 조회"""
    stmt = (
        select(Prediction)
        .where(and_(Prediction.race_id == race_id, Prediction.is_override == False))
        .order_by(Prediction.predicted_rank)
    )
    result = await db.execute(stmt)
    predictions = result.scalars().all()

    return [
        {
            "entry_id": p.entry_id,
            "total_score": p.total_score,
            "predicted_rank": p.predicted_rank,
            "confidence": p.confidence,
            "factors": p.factors_json,
            "model_version": p.model_version,
            "actual_rank": p.actual_rank,
        }
        for p in predictions
    ]


@router.post("/race/{race_id}/run")
async def run_prediction(race_id: int, db: AsyncSession = Depends(get_db)):
    """경주 예측 실행 (즉시)"""
    results = await predict_race(db, race_id)
    return {"race_id": race_id, "predictions": results}


@router.post("/override")
async def override_prediction(
    race_id: int,
    entry_id: int,
    new_jockey_id: int,
    db: AsyncSession = Depends(get_db),
):
    """수동 기수 변경 후 재예측"""
    # TODO: 기수 변경 시뮬레이션 구현
    return {
        "race_id": race_id,
        "entry_id": entry_id,
        "new_jockey_id": new_jockey_id,
        "status": "not_implemented",
    }
