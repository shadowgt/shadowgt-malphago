from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.jockey import Jockey
from app.models.race_entry import RaceEntry
from app.schemas.stats import JockeyStatsSchema

router = APIRouter()


@router.get("/{jockey_id}")
async def get_jockey(jockey_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Jockey).where(Jockey.id == jockey_id)
    result = await db.execute(stmt)
    jockey = result.scalar_one_or_none()
    if not jockey:
        raise HTTPException(status_code=404, detail="Jockey not found")
    return {
        "id": jockey.id,
        "name": jockey.name,
    }


@router.get("/{jockey_id}/stats", response_model=JockeyStatsSchema)
async def get_jockey_stats(jockey_id: int, db: AsyncSession = Depends(get_db)):
    """기수 상세 통계: 전적, 트랙별/거리별 승률, 최근 폼"""
    jockey = await db.get(Jockey, jockey_id)
    if not jockey:
        raise HTTPException(status_code=404, detail="Jockey not found")

    entries_q = (
        select(RaceEntry)
        .where(RaceEntry.jockey_id == jockey_id)
        .options(selectinload(RaceEntry.race))
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
    track_stats = {}
    for entry in entries:
        race = entry.race
        if not race:
            continue
        # 거리별
        if race.distance:
            dist = race.distance
            if dist not in distance_stats:
                distance_stats[dist] = {"total": 0, "wins": 0, "top3": 0}
            distance_stats[dist]["total"] += 1
            if entry.ranking == 1:
                distance_stats[dist]["wins"] += 1
            if entry.ranking and entry.ranking <= 3:
                distance_stats[dist]["top3"] += 1
        # 트랙별
        if race.track_id:
            tid = race.track_id
            if tid not in track_stats:
                track_stats[tid] = {"total": 0, "wins": 0, "top3": 0}
            track_stats[tid]["total"] += 1
            if entry.ranking == 1:
                track_stats[tid]["wins"] += 1
            if entry.ranking and entry.ranking <= 3:
                track_stats[tid]["top3"] += 1

    # 최근 30경주 폼
    recent_30 = entries[:30]
    recent_top3 = sum(1 for e in recent_30 if e.ranking and e.ranking <= 3)

    distance_breakdown = [
        {
            "distance": str(dist),
            "runs": s["total"],
            "wins": s["wins"],
            "top3": s["top3"],
            "win_rate": round(s["wins"] / s["total"] * 100, 1) if s["total"] > 0 else 0,
        }
        for dist, s in sorted(distance_stats.items())
    ]

    track_breakdown = [
        {
            "track": str(tid),
            "runs": s["total"],
            "wins": s["wins"],
            "win_rate": round(s["wins"] / s["total"] * 100, 1) if s["total"] > 0 else 0,
        }
        for tid, s in sorted(track_stats.items())
    ]

    return {
        "jockey_id": jockey_id,
        "name": jockey.name,
        "total_record": f"{total}-{wins}-{seconds}-{thirds}",
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "top3_rate": round((wins + seconds + thirds) / total * 100, 1) if total > 0 else 0,
        "recent_30_form": round(recent_top3 / len(recent_30) * 100, 1) if recent_30 else 0,
        "distance_breakdown": distance_breakdown,
        "track_breakdown": track_breakdown,
    }
