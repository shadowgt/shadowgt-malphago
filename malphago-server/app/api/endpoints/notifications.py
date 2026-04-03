"""알림 API — 변경 이력 조회 + FCM 구독"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entry_change_log import EntryChangeLog
from app.models.race import Race
from app.models.track import Track

router = APIRouter()


@router.get("/changes")
async def get_recent_changes(
    track: str = Query(None, description="트랙 코드 (S/B/J)"),
    race_date: date = Query(None, alias="date"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """최근 출전변경 이력 조회"""
    q = (
        select(EntryChangeLog, Race, Track)
        .join(Race, EntryChangeLog.race_id == Race.id)
        .join(Track, Race.track_id == Track.id)
        .order_by(EntryChangeLog.detected_at.desc())
        .limit(limit)
    )

    if track:
        q = q.where(Track.code == track.upper())
    if race_date:
        q = q.where(Race.race_date == race_date)

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "id": change.id,
            "race_id": change.race_id,
            "race_number": race.race_number,
            "race_date": race.race_date.isoformat(),
            "track": track_obj.code,
            "track_name": track_obj.name,
            "change_type": change.change_type,
            "field_name": change.field_name,
            "old_value": change.old_value,
            "new_value": change.new_value,
            "source": change.source,
            "detected_at": change.detected_at.isoformat() if change.detected_at else None,
        }
        for change, race, track_obj in rows
    ]


@router.post("/subscribe")
async def subscribe_to_changes(
    fcm_token: str = Query(..., description="FCM 디바이스 토큰"),
):
    """변경 알림 구독 (FCM 토픽 구독)

    Phase 2에서 구현. 현재는 토큰만 수신하여 확인 응답.
    실제 구현 시 Firebase Admin SDK로 토픽 구독 처리.
    """
    # TODO: Firebase Admin SDK로 토픽 구독
    # messaging.subscribe_to_topic([fcm_token], "race_changes")
    return {
        "status": "subscribed",
        "topic": "race_changes",
        "message": "경주 변경 알림이 활성화되었습니다.",
    }


@router.delete("/unsubscribe")
async def unsubscribe_from_changes(
    fcm_token: str = Query(..., description="FCM 디바이스 토큰"),
):
    """변경 알림 구독 해제"""
    # TODO: Firebase Admin SDK로 토픽 구독 해제
    return {
        "status": "unsubscribed",
        "topic": "race_changes",
    }
