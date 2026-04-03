"""등급 꼼수 감지 서비스

의도적으로 하위 등급에 체류하며 낮은 등급에서 우승을 노리는 패턴 감지.
감지 조건:
1. 최근 성적이 상위이나 등급이 올라가지 않은 경우
2. 특정 등급에서 반복적으로 상위 입상하는 패턴
3. 인기순위 대비 실제 순위가 지속적으로 좋은 경우 (의도적 저평가)
"""

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.race import Race
from app.models.race_entry import RaceEntry

logger = logging.getLogger(__name__)


async def detect_class_trick(
    session: AsyncSession, horse_id: int, recent_n: int = 10
) -> dict:
    """등급 꼼수 감지

    Returns:
        {
            "is_suspected": bool,
            "score": float (0~100, 높을수록 꼼수 의심),
            "reason": str,
            "detail": dict
        }
    """
    entries_q = (
        select(RaceEntry, Race.race_level, Race.distance)
        .join(Race, RaceEntry.race_id == Race.id)
        .where(RaceEntry.horse_id == horse_id)
        .order_by(RaceEntry.id.desc())
        .limit(recent_n)
    )
    result = await session.execute(entries_q)
    rows = result.all()

    if len(rows) < 3:
        return {"is_suspected": False, "score": 0.0, "reason": "데이터 부족", "detail": {}}

    entries = [(r[0], r.race_level, r.distance) for r in rows]

    # 1. 동일 등급 체류 + 반복 상위 입상
    level_results: dict[str, list[int]] = {}
    for entry, level, _ in entries:
        if not level or entry.ranking is None:
            continue
        num = _level_num(level)
        if num is None:
            continue
        key = str(num)
        if key not in level_results:
            level_results[key] = []
        level_results[key].append(entry.ranking)

    # 동일 등급에서 3회 이상 출전 + top3 비율 60% 이상
    same_level_trick = 0.0
    trick_level = None
    for level, rankings in level_results.items():
        if len(rankings) >= 3:
            top3_rate = sum(1 for r in rankings if r <= 3) / len(rankings)
            if top3_rate >= 0.6:
                same_level_trick = top3_rate * 60
                trick_level = level

    # 2. 인기순위 대비 실제 순위 차이 (저평가 패턴)
    underperform_count = 0
    for entry, _, _ in entries:
        if entry.ranking and entry.favor_ranking:
            if entry.ranking < entry.favor_ranking - 1:
                underperform_count += 1  # 인기보다 훨씬 좋은 결과

    underperform_score = min(underperform_count * 10, 40)

    total_score = same_level_trick + underperform_score
    is_suspected = total_score >= 50

    reasons = []
    if same_level_trick > 0 and trick_level:
        reasons.append(f"등급 {trick_level}에서 반복 상위 입상")
    if underperform_count >= 3:
        reasons.append(f"인기순위 대비 과소평가 패턴 ({underperform_count}회)")

    return {
        "is_suspected": is_suspected,
        "score": min(total_score, 100.0),
        "reason": " + ".join(reasons) if reasons else "정상",
        "detail": {
            "level_results": {k: len(v) for k, v in level_results.items()},
            "underperform_count": underperform_count,
        },
    }


def _level_num(level: str | None) -> int | None:
    if not level:
        return None
    match = re.search(r"(\d+)", level)
    return int(match.group(1)) if match else None


async def calc_class_trick_score(
    session: AsyncSession, horse_id: int
) -> float:
    """등급 꼼수 보정 점수 → 0~100 (예측 모델 입력용)

    꼼수가 의심되면 해당 말의 예측 점수를 상향 보정.
    """
    result = await detect_class_trick(session, horse_id)
    if result["is_suspected"]:
        # 꼼수 의심 → 보너스 (실제 능력이 등급 대비 높음)
        return min(50.0 + result["score"] * 0.3, 80.0)
    return 50.0
