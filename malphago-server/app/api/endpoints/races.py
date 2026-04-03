from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.schemas.race import RaceSchema

router = APIRouter()


@router.get("", response_model=list[RaceSchema])
async def list_races(
    track: str | None = Query(None, description="경마장 코드 (S/B/J)"),
    race_date: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Race)
    if track:
        from app.models.track import Track

        stmt = stmt.join(Track).where(Track.code == track.upper())
    if race_date:
        stmt = stmt.where(Race.race_date == race_date)
    stmt = stmt.order_by(Race.race_date.desc(), Race.race_number)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{race_id}", response_model=RaceSchema | None)
async def get_race(race_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Race).where(Race.id == race_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/{race_id}/entries")
async def get_race_entries(race_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(RaceEntry)
        .where(RaceEntry.race_id == race_id)
        .options(
            selectinload(RaceEntry.horse),
            selectinload(RaceEntry.jockey),
            selectinload(RaceEntry.trainer),
            selectinload(RaceEntry.timing),
        )
        .order_by(RaceEntry.horse_number)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
