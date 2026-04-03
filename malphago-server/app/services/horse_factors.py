"""말 분석 요인 — Phase 2 신규 요인

거리적성, 주로적성, 휴식기간, 게이트 포지션은 기존 prediction.py에 있으나
여기서는 Phase 2 신규 요인을 추가로 구현:
- surface_aptitude: 주로상태별 성적 (잔디/모래 + 함수율)
- class_movement: 등급 이동 시 성적 변화 감지
- running_style_matching: 각질 매칭 점수
- horse_weight_factor: 마체중 변동 분석
"""

import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.services.running_style import (
    analyze_running_style,
    RunningStyle,
)

logger = logging.getLogger(__name__)


async def calc_surface_aptitude(
    session: AsyncSession, horse_id: int, target_surface: str | None, target_moisture: str | None
) -> float:
    """주로상태 적성 → 0~100

    잔디/모래 + 함수율(건조/약간습/습/불량) 조합별 성적 분석.
    """
    if not target_surface:
        return 50.0

    entries_q = (
        select(RaceEntry, Race.surface, Race.moisture)
        .join(Race, RaceEntry.race_id == Race.id)
        .where(RaceEntry.horse_id == horse_id)
    )
    result = await session.execute(entries_q)
    rows = result.all()
    if not rows:
        return 50.0

    # 동일 주로에서의 성적
    same_surface = [r for r in rows if r.surface == target_surface]
    if not same_surface:
        return 40.0  # 해당 주로 경험 없음

    top3_same = sum(1 for r in same_surface if r[0].ranking is not None and r[0].ranking <= 3)
    surface_rate = (top3_same / len(same_surface)) * 100

    # 함수율 보정: 동일 moisture 경험이 있으면 보너스
    if target_moisture:
        same_moisture = [r for r in same_surface if r.moisture == target_moisture]
        if same_moisture:
            top3_moisture = sum(1 for r in same_moisture if r[0].ranking is not None and r[0].ranking <= 3)
            moisture_rate = (top3_moisture / len(same_moisture)) * 100
            # 가중 평균 (주로 70% + 함수율 30%)
            return min(surface_rate * 0.7 + moisture_rate * 0.3, 100.0)

    return min(surface_rate, 100.0)


async def calc_class_movement(
    session: AsyncSession, horse_id: int, target_level: str | None
) -> float:
    """등급 이동 점수 → 0~100

    등급 하락 시 유리 (높은 점수), 등급 상승 시 불리.
    등급 체계: 숫자가 작을수록 상위 (국1 > 국2 > ... > 국6).
    """
    if not target_level:
        return 50.0

    entries_q = (
        select(RaceEntry, Race.race_level)
        .join(Race, RaceEntry.race_id == Race.id)
        .where(RaceEntry.horse_id == horse_id)
        .order_by(RaceEntry.id.desc())
        .limit(5)
    )
    result = await session.execute(entries_q)
    rows = result.all()
    if not rows:
        return 50.0

    target_num = _level_to_number(target_level)
    if target_num is None:
        return 50.0

    # 최근 경주 등급과 비교
    recent_levels = [_level_to_number(r.race_level) for r in rows if r.race_level]
    recent_levels = [l for l in recent_levels if l is not None]
    if not recent_levels:
        return 50.0

    avg_recent = sum(recent_levels) / len(recent_levels)
    diff = avg_recent - target_num  # 양수 = 등급 하락 (유리)

    if diff > 1:
        return 80.0  # 등급 크게 하락 → 매우 유리
    elif diff > 0:
        return 65.0  # 약간 하락
    elif diff == 0:
        return 50.0  # 동일
    elif diff > -1:
        return 40.0  # 약간 상승
    else:
        return 25.0  # 등급 크게 상승 → 불리


def _level_to_number(level: str | None) -> int | None:
    """등급 문자열 → 숫자 (국1=1, 국2=2, ... 국6=6)"""
    if not level:
        return None
    # "국3", "3", "국제3" 등 다양한 형태
    import re
    match = re.search(r"(\d+)", level)
    if match:
        return int(match.group(1))
    return None


async def calc_running_style_matching(
    session: AsyncSession,
    horse_id: int,
    jockey_id: int | None,
    race_distance: int | None,
) -> float:
    """각질 매칭 점수 → 0~100

    말의 각질과 기수의 선호 전법이 일치하는지 분석.
    또한 거리별 각질 유리도를 반영:
    - 단거리(~1200m): 도주/선행 유리
    - 중거리(1300~1700m): 선행/선입 유리
    - 장거리(1800m~): 추입/자재 유리
    """
    horse_analysis = await analyze_running_style(session, horse_id, recent_n=10)
    if horse_analysis.sample_count == 0:
        return 50.0

    horse_style = horse_analysis.style
    base_score = 50.0

    # 1. 일관성 보너스 (각질이 일정한 말이 예측 가능성 높음)
    consistency_bonus = horse_analysis.consistency * 20  # 0~20점

    # 2. 거리별 각질 유리도
    distance_bonus = 0.0
    if race_distance:
        if race_distance <= 1200:
            # 단거리: 도주/선행 유리
            if horse_style in (RunningStyle.FRONT_RUNNER, RunningStyle.STALKER):
                distance_bonus = 15.0
            elif horse_style == RunningStyle.MID_PACK:
                distance_bonus = 5.0
            elif horse_style == RunningStyle.CLOSER:
                distance_bonus = -10.0
        elif race_distance <= 1700:
            # 중거리: 선행/선입 유리
            if horse_style in (RunningStyle.STALKER, RunningStyle.MID_PACK):
                distance_bonus = 15.0
            elif horse_style == RunningStyle.VERSATILE:
                distance_bonus = 10.0
        else:
            # 장거리: 추입/자재 유리
            if horse_style in (RunningStyle.CLOSER, RunningStyle.VERSATILE):
                distance_bonus = 15.0
            elif horse_style == RunningStyle.FRONT_RUNNER:
                distance_bonus = -10.0

    # 3. 기수의 주행 패턴과 말의 각질 매칭
    jockey_bonus = 0.0
    if jockey_id:
        jockey_bonus = await _calc_jockey_style_match(session, jockey_id, horse_style)

    total = base_score + consistency_bonus + distance_bonus + jockey_bonus
    return max(0.0, min(total, 100.0))


async def _calc_jockey_style_match(
    session: AsyncSession, jockey_id: int, horse_style: RunningStyle
) -> float:
    """기수가 해당 각질의 말과 탈 때 성적이 좋은지 분석 → -10~+15"""
    # 기수의 최근 기승 말들의 각질별 성적
    entries_q = (
        select(RaceEntry)
        .where(RaceEntry.jockey_id == jockey_id)
        .order_by(RaceEntry.id.desc())
        .limit(30)
    )
    result = await session.execute(entries_q)
    entries = result.scalars().all()
    if not entries:
        return 0.0

    style_results: dict[RunningStyle, list[int]] = {}
    for entry in entries:
        if not entry.horse_id or entry.ranking is None:
            continue
        horse_analysis = await analyze_running_style(session, entry.horse_id, recent_n=5)
        if horse_analysis.sample_count == 0:
            continue
        style = horse_analysis.style
        if style not in style_results:
            style_results[style] = []
        style_results[style].append(entry.ranking)

    if horse_style not in style_results:
        return 0.0

    results = style_results[horse_style]
    top3_rate = sum(1 for r in results if r <= 3) / len(results) if results else 0

    # 전체 평균과 비교
    all_results = [r for rs in style_results.values() for r in rs]
    avg_top3 = sum(1 for r in all_results if r <= 3) / len(all_results) if all_results else 0

    diff = top3_rate - avg_top3
    return diff * 50  # -10 ~ +15 범위


async def calc_horse_weight_factor(
    session: AsyncSession, horse_id: int
) -> float:
    """마체중 변동 분석 → 0~100

    급격한 체중 변화는 컨디션 문제 시사.
    최적: 변화 ±5kg 이내
    """
    entries_q = (
        select(RaceEntry)
        .where(RaceEntry.horse_id == horse_id)
        .order_by(RaceEntry.id.desc())
        .limit(5)
    )
    result = await session.execute(entries_q)
    entries = result.scalars().all()
    if not entries:
        return 50.0

    # 최근 경주의 마체중 변화
    latest = entries[0]
    if latest.horse_weight_change is None:
        return 50.0

    change = abs(latest.horse_weight_change)
    if change <= 4:
        return 80.0  # 안정적
    elif change <= 8:
        return 65.0  # 소폭 변화
    elif change <= 15:
        return 45.0  # 주의 필요
    else:
        return 25.0  # 큰 변화 → 위험 신호
