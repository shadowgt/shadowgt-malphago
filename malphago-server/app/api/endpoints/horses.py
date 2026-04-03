from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.horse import Horse
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming
from app.schemas.stats import HorseStatsSchema

router = APIRouter()


@router.get("/{horse_id}")
async def get_horse(horse_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Horse).where(Horse.id == horse_id)
    result = await db.execute(stmt)
    horse = result.scalar_one_or_none()
    if not horse:
        raise HTTPException(status_code=404, detail="Horse not found")
    return horse


@router.get("/{horse_id}/stats", response_model=HorseStatsSchema)
async def get_horse_stats(horse_id: int, db: AsyncSession = Depends(get_db)):
    """말 상세 통계: 전적, 거리별 성적, 최근 10경주"""
    horse = await db.get(Horse, horse_id)
    if not horse:
        raise HTTPException(status_code=404, detail="Horse not found")

    # 전체 전적
    entries_q = (
        select(RaceEntry)
        .where(RaceEntry.horse_id == horse_id)
        .order_by(RaceEntry.id.desc())
    )
    entries_result = await db.execute(entries_q)
    entries = entries_result.scalars().all()

    total = len(entries)
    wins = sum(1 for e in entries if e.ranking == 1)
    seconds = sum(1 for e in entries if e.ranking == 2)
    thirds = sum(1 for e in entries if e.ranking == 3)

    # 거리별 성적
    distance_stats = {}
    for entry in entries:
        race = await db.get(Race, entry.race_id)
        if not race or not race.distance:
            continue
        dist = race.distance
        if dist not in distance_stats:
            distance_stats[dist] = {"total": 0, "wins": 0, "top3": 0}
        distance_stats[dist]["total"] += 1
        if entry.ranking == 1:
            distance_stats[dist]["wins"] += 1
        if entry.ranking and entry.ranking <= 3:
            distance_stats[dist]["top3"] += 1

    # 최근 10경주
    recent = []
    for entry in entries[:10]:
        race = await db.get(Race, entry.race_id)
        recent.append({
            "race_date": race.race_date.isoformat() if race else None,
            "track_code": None,
            "race_number": race.race_number if race else None,
            "distance": race.distance if race else None,
            "ranking": entry.ranking,
            "horse_weight": entry.horse_weight,
            "odds_win": float(entry.odds_win) if entry.odds_win else None,
        })

    return {
        "horse_id": horse_id,
        "name": horse.name,
        "origin": horse.origin,
        "gender": horse.gender,
        "total_record": f"{total}-{wins}-{seconds}-{thirds}",
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "top3_rate": round((wins + seconds + thirds) / total * 100, 1) if total > 0 else 0,
        "distance_stats": distance_stats,
        "recent_races": recent,
    }
