from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.prediction import Prediction

router = APIRouter()


@router.get("/race/{race_id}")
async def get_race_predictions(race_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Prediction)
        .where(Prediction.race_id == race_id, Prediction.is_override == False)
        .order_by(Prediction.predicted_rank)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/override")
async def override_prediction(
    race_id: int,
    entry_id: int,
    new_jockey_id: int,
    db: AsyncSession = Depends(get_db),
):
    # TODO: 기수 변경 후 재예측 로직
    return {
        "race_id": race_id,
        "entry_id": entry_id,
        "new_jockey_id": new_jockey_id,
        "status": "not_implemented",
    }
