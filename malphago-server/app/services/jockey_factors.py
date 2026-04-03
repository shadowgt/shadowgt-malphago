"""기수 분석 요인 — Phase 2

- jockey_fatigue: 당일 다중 기승 시 피로도 감점
- apprentice_bonus: 수습기수 부담중량 보정
"""

import logging
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.race import Race
from app.models.race_entry import RaceEntry

logger = logging.getLogger(__name__)


async def calc_jockey_fatigue(
    session: AsyncSession,
    jockey_id: int | None,
    race_date: date,
    race_number: int,
    track_id: int,
) -> float:
    """기수 피로도 점수 → 0~100

    당일 기승 순서가 늦을수록 피로 누적.
    동일 경마장에서 5경주 이상 연속 기승 시 감점.
    """
    if not jockey_id:
        return 50.0

    # 해당 날짜+트랙에서 이 기수의 기승 경주 목록
    q = (
        select(Race.race_number)
        .join(RaceEntry, RaceEntry.race_id == Race.id)
        .where(
            and_(
                RaceEntry.jockey_id == jockey_id,
                Race.race_date == race_date,
                Race.track_id == track_id,
            )
        )
        .order_by(Race.race_number)
    )
    result = await session.execute(q)
    race_numbers = [r[0] for r in result.all()]

    if not race_numbers:
        return 70.0  # 데이터 없으면 기본값

    total_rides = len(race_numbers)
    # 현재 경주가 당일 몇 번째 기승인지
    ride_order = sum(1 for rn in race_numbers if rn <= race_number)

    # 기본 점수
    if total_rides <= 2:
        base = 85.0  # 적은 기승 → 좋은 컨디션
    elif total_rides <= 4:
        base = 75.0
    elif total_rides <= 6:
        base = 65.0
    else:
        base = 55.0  # 7경주 이상 → 높은 피로

    # 기승 순서 감점: 후반 경주일수록 -2점/경주
    order_penalty = max(0, (ride_order - 2)) * 3

    return max(20.0, min(base - order_penalty, 100.0))


def calc_apprentice_bonus(weight_str: str | None) -> float:
    """수습기수 부담중량 보정 → 0~100

    수습기수는 부담중량 경감 혜택으로 경주 유리.
    일반적으로 부담중량이 낮을수록 유리.
    """
    if not weight_str:
        return 50.0

    try:
        weight = float(weight_str)
    except (ValueError, TypeError):
        return 50.0

    # 표준 부담중량: 57kg (일반), 수습기수는 52~55kg
    if weight <= 52:
        return 80.0  # 수습기수 최대 경감
    elif weight <= 54:
        return 70.0
    elif weight <= 56:
        return 55.0  # 일반
    elif weight <= 58:
        return 45.0
    else:
        return 35.0  # 과중량
