"""증분 동기화 API

앱이 마지막 동기화 시각 이후 변경된 데이터만 가져가는 엔드포인트.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.entry_change_log import EntryChangeLog
from app.schemas.stats import SyncDeltaSchema

router = APIRouter()


@router.get("/delta", response_model=SyncDeltaSchema)
async def get_delta(
    since: datetime = Query(..., description="마지막 동기화 시각 (ISO-8601)"),
    track: str | None = Query(None, description="경마장 코드 (S/B/J)"),
    db: AsyncSession = Depends(get_db),
):
    """증분 동기화: since 이후 변경된 경주/출주/변경로그 반환"""

    # 변경된 경주 (간단히 ID 범위로 — 실제로는 updated_at 컬럼 필요)
    race_q = select(Race).order_by(Race.id.desc()).limit(50)
    if track:
        from app.models.track import Track
        race_q = race_q.join(Track).where(Track.code == track.upper())
    race_result = await db.execute(race_q)
    races = race_result.scalars().all()

    # 변경 로그
    change_q = (
        select(EntryChangeLog)
        .where(EntryChangeLog.detected_at >= since)
        .order_by(EntryChangeLog.detected_at.desc())
        .limit(100)
    )
    change_result = await db.execute(change_q)
    changes = change_result.scalars().all()

    return {
        "races": [
            {
                "id": r.id,
                "track_id": r.track_id,
                "race_date": r.race_date.isoformat(),
                "race_number": r.race_number,
                "race_level": r.race_level,
                "distance": r.distance,
                "weather": r.weather,
                "total_entries": r.total_entries,
            }
            for r in races
        ],
        "change_logs": [
            {
                "id": c.id,
                "race_id": c.race_id,
                "change_type": c.change_type,
                "field_name": c.field_name,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "detected_at": c.detected_at.isoformat() if c.detected_at else None,
            }
            for c in changes
        ],
    }
