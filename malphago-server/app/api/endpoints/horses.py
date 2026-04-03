from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.horse import Horse

router = APIRouter()


@router.get("/{horse_id}")
async def get_horse(horse_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Horse).where(Horse.id == horse_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/{horse_id}/stats")
async def get_horse_stats(horse_id: int, db: AsyncSession = Depends(get_db)):
    # TODO: 통계 계산 서비스 연동
    return {"horse_id": horse_id, "stats": "not_implemented"}
