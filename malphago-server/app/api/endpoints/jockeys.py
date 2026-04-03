from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.jockey import Jockey

router = APIRouter()


@router.get("/{jockey_id}")
async def get_jockey(jockey_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Jockey).where(Jockey.id == jockey_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/{jockey_id}/stats")
async def get_jockey_stats(jockey_id: int, db: AsyncSession = Depends(get_db)):
    # TODO: 통계 계산 서비스 연동
    return {"jockey_id": jockey_id, "stats": "not_implemented"}
