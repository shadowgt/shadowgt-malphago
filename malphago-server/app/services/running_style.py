"""각질(走質) 자동 분류 서비스

코너순위, S1F(초반1F), G1F(끝1F), G3F(끝3F) 데이터를 분석하여
말의 주행 스타일을 자동 분류한다.

각질 유형:
- 도주(逃走): 선두에서 끝까지 달리는 스타일
- 선행(先行): 선두 그룹에서 달리다 후반 추월
- 선입(先入): 중간 위치에서 꾸준히 전진
- 추입(追入): 후방에서 출발하여 후반 폭발적 추월
- 자재(自在): 상황에 따라 유연하게 대응

분류 기준:
1. 평균 코너순위 (corner_1~4의 평균 위치)
2. S1F 대비 G1F 변화율 (초반 vs 후반 속도 변화)
3. G3F 대비 전체 기록 비율 (후반 가속 정도)
"""

import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming

logger = logging.getLogger(__name__)


class RunningStyle(str, Enum):
    FRONT_RUNNER = "도주"    # 逃走: leads from start to finish
    STALKER = "선행"         # 先行: near the front, kicks late
    MID_PACK = "선입"        # 先入: middle of the pack, steady advance
    CLOSER = "추입"          # 追入: comes from behind with a big finish
    VERSATILE = "자재"       # 自在: adapts to race conditions
    UNKNOWN = "미분류"


@dataclass
class RunningStyleAnalysis:
    """각질 분석 결과"""
    style: RunningStyle = RunningStyle.UNKNOWN
    avg_corner_position: float = 0.0
    early_speed_score: float = 0.0     # S1F 기반 초반 스피드 (낮을수록 빠름)
    late_kick_score: float = 0.0       # G1F 기반 후반 추진력
    acceleration_ratio: float = 0.0     # S1F/G1F 비율 (>1: 후반 가속)
    consistency: float = 0.0           # 스타일 일관성 (0~1)
    sample_count: int = 0              # 분석에 사용된 경주 수


def _parse_corner(corner_str: str | None) -> int | None:
    """코너 순위 문자열을 정수로 변환 (예: '3' → 3, '02' → 2)"""
    if not corner_str:
        return None
    try:
        return int(corner_str.strip())
    except (ValueError, TypeError):
        return None


def classify_single_race(timing: RaceTiming, total_entries: int | None) -> RunningStyle:
    """단일 경주의 타이밍 데이터로 각질 분류

    Args:
        timing: 경주 타이밍 데이터
        total_entries: 해당 경주의 총 출주두수

    Returns:
        RunningStyle enum
    """
    if not total_entries or total_entries < 2:
        return RunningStyle.UNKNOWN

    # 코너 순위 파싱
    corners = [
        _parse_corner(timing.corner_1),
        _parse_corner(timing.corner_2),
        _parse_corner(timing.corner_3),
        _parse_corner(timing.corner_4),
    ]
    valid_corners = [c for c in corners if c is not None]

    if not valid_corners:
        return RunningStyle.UNKNOWN

    avg_pos = sum(valid_corners) / len(valid_corners)
    # 상대 위치 (0.0=선두, 1.0=꼴찌)
    relative_pos = (avg_pos - 1) / (total_entries - 1) if total_entries > 1 else 0.5

    # 코너간 순위 변화 (후반 순위 상승 여부)
    if len(valid_corners) >= 2:
        first_corner = valid_corners[0]
        last_corner = valid_corners[-1]
        position_change = first_corner - last_corner  # 양수면 순위 상승
    else:
        position_change = 0

    # S1F / G1F 속도 비율
    s1f = float(timing.s1f) if timing.s1f else None
    g1f = float(timing.g1f) if timing.g1f else None

    if s1f and g1f and g1f > 0:
        speed_ratio = s1f / g1f  # >1이면 후반이 더 빠름 (가속)
    else:
        speed_ratio = 1.0

    # 분류 로직
    if relative_pos <= 0.15:
        # 거의 항상 선두
        if position_change >= 0:
            return RunningStyle.FRONT_RUNNER  # 도주
        else:
            return RunningStyle.STALKER  # 선행 (선두였으나 약간 밀림)
    elif relative_pos <= 0.35:
        # 선두 그룹
        if speed_ratio > 1.05:
            return RunningStyle.STALKER  # 선행 (후반 가속)
        else:
            return RunningStyle.FRONT_RUNNER  # 도주에 가까움
    elif relative_pos <= 0.55:
        # 중간 그룹
        if position_change > 1:
            return RunningStyle.MID_PACK  # 선입 (중간→앞으로 전진)
        else:
            return RunningStyle.VERSATILE  # 자재
    elif relative_pos <= 0.75:
        # 후방 그룹
        if position_change > 2 or speed_ratio > 1.1:
            return RunningStyle.CLOSER  # 추입
        else:
            return RunningStyle.MID_PACK  # 선입
    else:
        # 최후방
        if position_change > 3:
            return RunningStyle.CLOSER  # 추입 (후방에서 대역전)
        else:
            return RunningStyle.CLOSER  # 추입


async def analyze_running_style(
    session: AsyncSession, horse_id: int, recent_n: int = 10
) -> RunningStyleAnalysis:
    """말의 최근 N경주 데이터로 각질 종합 분석

    Args:
        session: DB 세션
        horse_id: 말 ID
        recent_n: 분석할 최근 경주 수

    Returns:
        RunningStyleAnalysis
    """
    # 최근 N경주의 entry + timing 조회
    entries_q = (
        select(RaceEntry)
        .where(RaceEntry.horse_id == horse_id)
        .options(selectinload(RaceEntry.timing))
        .order_by(RaceEntry.id.desc())
        .limit(recent_n)
    )
    result = await session.execute(entries_q)
    entries = result.scalars().all()

    if not entries:
        return RunningStyleAnalysis()

    # 각 경주별 각질 분류
    style_counts: dict[RunningStyle, int] = {}
    corner_positions: list[float] = []
    s1f_values: list[float] = []
    g1f_values: list[float] = []
    analyzed = 0

    for entry in entries:
        if not entry.timing:
            continue

        # 총 출주두수 조회
        from app.models.race import Race
        race = await session.get(Race, entry.race_id)
        total_entries = race.total_entries if race else None

        style = classify_single_race(entry.timing, total_entries)
        if style != RunningStyle.UNKNOWN:
            style_counts[style] = style_counts.get(style, 0) + 1
            analyzed += 1

        # 코너 순위 수집
        corners = [
            _parse_corner(entry.timing.corner_1),
            _parse_corner(entry.timing.corner_2),
            _parse_corner(entry.timing.corner_3),
            _parse_corner(entry.timing.corner_4),
        ]
        valid_corners = [c for c in corners if c is not None]
        if valid_corners:
            corner_positions.append(sum(valid_corners) / len(valid_corners))

        # 속도 데이터 수집
        if entry.timing.s1f:
            s1f_values.append(float(entry.timing.s1f))
        if entry.timing.g1f:
            g1f_values.append(float(entry.timing.g1f))

    if not analyzed:
        return RunningStyleAnalysis(sample_count=0)

    # 최빈 스타일 결정
    dominant_style = max(style_counts, key=style_counts.get)
    dominant_count = style_counts[dominant_style]
    consistency = dominant_count / analyzed

    # 평균 통계
    avg_corner = sum(corner_positions) / len(corner_positions) if corner_positions else 0
    avg_s1f = sum(s1f_values) / len(s1f_values) if s1f_values else 0
    avg_g1f = sum(g1f_values) / len(g1f_values) if g1f_values else 0
    accel_ratio = avg_s1f / avg_g1f if avg_g1f > 0 else 1.0

    return RunningStyleAnalysis(
        style=dominant_style,
        avg_corner_position=round(avg_corner, 1),
        early_speed_score=round(avg_s1f, 2),
        late_kick_score=round(avg_g1f, 2),
        acceleration_ratio=round(accel_ratio, 3),
        consistency=round(consistency, 2),
        sample_count=analyzed,
    )


async def analyze_race_running_styles(
    session: AsyncSession, race_id: int
) -> dict[int, RunningStyleAnalysis]:
    """경주 전체 출주마의 각질 일괄 분석

    Returns:
        {horse_id: RunningStyleAnalysis}
    """
    entries_q = select(RaceEntry).where(RaceEntry.race_id == race_id)
    result = await session.execute(entries_q)
    entries = result.scalars().all()

    analyses = {}
    for entry in entries:
        if entry.horse_id:
            analysis = await analyze_running_style(session, entry.horse_id)
            analyses[entry.horse_id] = analysis

    return analyses
