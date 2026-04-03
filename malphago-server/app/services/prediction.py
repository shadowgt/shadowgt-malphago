"""가중 선형 예측 모델 (Phase 2)

기획서 기반 가중치 + Phase 2 신규 요인:
  말 기본 승률(0.10) + 거리적성(0.10) + 주로적성(0.08) +
  폼지수(0.08) + 클래스이동(0.06) + 게이트(0.04) +
  기수승률(0.08) + 기수트랙특화(0.05) + 기수피로도(0.04) +
  조교사시너지(0.08) + 말-기수시너지(0.08) +
  휴식기간(0.04) + 각질매칭(0.07) + 마체중변동(0.04) +
  등급꼼수(0.06)

각 요인은 0~100 범위로 정규화하여 종합점수를 산출한다.
"""

import json
import logging
from dataclasses import dataclass, field, asdict

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming
from app.models.prediction import Prediction
from app.services.synergy import calculate_synergy
from app.services.horse_factors import (
    calc_surface_aptitude,
    calc_class_movement,
    calc_running_style_matching,
    calc_horse_weight_factor,
)
from app.services.jockey_factors import calc_jockey_fatigue, calc_apprentice_bonus
from app.services.class_trick_detector import calc_class_trick_score

logger = logging.getLogger(__name__)

MODEL_VERSION = "weighted_linear_v2"

# 가중치 (Phase 2 — 20개 요인, 합계 1.00)
WEIGHTS = {
    "horse_win_rate": 0.10,
    "distance_aptitude": 0.10,
    "surface_aptitude": 0.08,
    "form_index": 0.08,
    "class_movement": 0.06,
    "gate_position": 0.04,
    "jockey_win_rate": 0.08,
    "jockey_track_spec": 0.05,
    "jockey_fatigue": 0.04,
    "trainer_synergy": 0.08,
    "horse_jockey_synergy": 0.08,
    "rest_period": 0.04,
    "running_style_match": 0.07,
    "horse_weight_factor": 0.04,
    "class_trick": 0.06,
}


@dataclass
class PredictionFactors:
    """예측 요인 분해"""
    horse_win_rate: float = 0.0
    distance_aptitude: float = 0.0
    surface_aptitude: float = 0.0
    form_index: float = 0.0
    class_movement: float = 0.0
    gate_position: float = 0.0
    jockey_win_rate: float = 0.0
    jockey_track_spec: float = 0.0
    jockey_fatigue: float = 0.0
    trainer_synergy: float = 0.0
    horse_jockey_synergy: float = 0.0
    rest_period: float = 0.0
    running_style_match: float = 0.0
    horse_weight_factor: float = 0.0
    class_trick: float = 0.0


async def _calc_horse_win_rate(session: AsyncSession, horse_id: int) -> float:
    """말 기본 승률 (3위이내 입상률) → 0~100"""
    entries_q = select(RaceEntry).where(RaceEntry.horse_id == horse_id)
    result = await session.execute(entries_q)
    entries = result.scalars().all()
    if not entries:
        return 50.0  # 데이터 없으면 중간값
    top3 = sum(1 for e in entries if e.ranking is not None and e.ranking <= 3)
    return min((top3 / len(entries)) * 100, 100.0)


async def _calc_distance_aptitude(
    session: AsyncSession, horse_id: int, target_distance: int
) -> float:
    """거리 적성 (해당 거리에서의 입상률 vs 전체) → 0~100"""
    if not target_distance:
        return 50.0

    entries_q = (
        select(RaceEntry, Race.distance)
        .join(Race, RaceEntry.race_id == Race.id)
        .where(RaceEntry.horse_id == horse_id)
    )
    result = await session.execute(entries_q)
    rows = result.all()
    if not rows:
        return 50.0

    # 거리 범위: ±200m 이내를 "동일 거리"로 간주
    same_dist = [r for r in rows if r.distance and abs(r.distance - target_distance) <= 200]
    if not same_dist:
        return 40.0  # 해당 거리 경험 없으면 약간 감점

    top3_same = sum(1 for r in same_dist if r[0].ranking is not None and r[0].ranking <= 3)
    rate = (top3_same / len(same_dist)) * 100
    return min(rate, 100.0)


async def _calc_form_index(session: AsyncSession, horse_id: int) -> float:
    """최근 폼 지수 (최근 5경주 가중 평균) → 0~100"""
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

    # 가중치: 최근일수록 높은 가중치 (5, 4, 3, 2, 1)
    weights = [5, 4, 3, 2, 1]
    total_weight = 0
    weighted_score = 0

    for i, entry in enumerate(entries):
        w = weights[i] if i < len(weights) else 1
        total_weight += w
        if entry.ranking is not None:
            # 1위=100, 2위=80, 3위=60, 이하 점진 하락
            if entry.ranking == 1:
                score = 100
            elif entry.ranking == 2:
                score = 80
            elif entry.ranking == 3:
                score = 60
            elif entry.ranking <= 5:
                score = 40
            else:
                score = max(20, 100 - entry.ranking * 8)
            weighted_score += w * score
        else:
            weighted_score += w * 30  # 순위 미기록

    return min(weighted_score / total_weight, 100.0)


async def _calc_jockey_win_rate(session: AsyncSession, jockey_id: int) -> float:
    """기수 승률 → 0~100"""
    entries_q = select(RaceEntry).where(RaceEntry.jockey_id == jockey_id)
    result = await session.execute(entries_q)
    entries = result.scalars().all()
    if not entries:
        return 50.0
    wins = sum(1 for e in entries if e.ranking == 1)
    # 승률을 확대해서 0~100 범위로 (승률 20%이상이면 거의 최고)
    return min((wins / len(entries)) * 500, 100.0)


async def _calc_jockey_track_spec(
    session: AsyncSession, jockey_id: int, track_id: int
) -> float:
    """기수 트랙 특화도 → 0~100"""
    all_q = select(RaceEntry).where(RaceEntry.jockey_id == jockey_id)
    all_result = await session.execute(all_q)
    all_entries = all_result.scalars().all()
    if not all_entries:
        return 50.0

    track_q = (
        select(RaceEntry)
        .join(Race, RaceEntry.race_id == Race.id)
        .where(and_(RaceEntry.jockey_id == jockey_id, Race.track_id == track_id))
    )
    track_result = await session.execute(track_q)
    track_entries = track_result.scalars().all()
    if not track_entries:
        return 40.0

    all_win_rate = sum(1 for e in all_entries if e.ranking == 1) / len(all_entries)
    track_win_rate = sum(1 for e in track_entries if e.ranking == 1) / len(track_entries)

    # 트랙 특화도: 트랙 승률 / 전체 승률 비율
    if all_win_rate > 0:
        ratio = track_win_rate / all_win_rate
        return min(ratio * 50, 100.0)  # 1.0 = 50점, 2.0 = 100점
    return 50.0


def _calc_gate_position(horse_number: int | None, total_entries: int | None) -> float:
    """게이트 포지션 점수 → 0~100 (안쪽이 유리한 경향)"""
    if not horse_number or not total_entries or total_entries == 0:
        return 50.0
    # 안쪽 마번일수록 유리 (단거리 기준)
    position_ratio = horse_number / total_entries
    return max(0, 100 - position_ratio * 60)  # 1번 마번 ≈ 94, 마지막 마번 ≈ 40


def _calc_rest_period(race_interval: int | None) -> float:
    """휴식기간 점수 → 0~100 (최적: 14~42일)"""
    if race_interval is None:
        return 50.0
    if 14 <= race_interval <= 42:
        return 80.0  # 최적 구간
    elif 7 <= race_interval < 14:
        return 65.0  # 약간 짧음
    elif 42 < race_interval <= 90:
        return 60.0  # 약간 긴 휴식
    elif race_interval > 90:
        return 35.0  # 장기 공백
    else:
        return 45.0  # 너무 짧음


async def predict_entry(
    session: AsyncSession,
    entry: RaceEntry,
    race: Race,
) -> tuple[float, PredictionFactors]:
    """단일 출주마 예측 점수 계산"""
    factors = PredictionFactors()

    # 각 요인 계산
    factors.horse_win_rate = await _calc_horse_win_rate(session, entry.horse_id)
    factors.distance_aptitude = await _calc_distance_aptitude(
        session, entry.horse_id, race.distance
    )
    factors.form_index = await _calc_form_index(session, entry.horse_id)
    factors.jockey_win_rate = await _calc_jockey_win_rate(session, entry.jockey_id)
    factors.jockey_track_spec = await _calc_jockey_track_spec(
        session, entry.jockey_id, race.track_id
    )
    factors.gate_position = _calc_gate_position(entry.horse_number, race.total_entries)
    factors.rest_period = _calc_rest_period(entry.race_interval)

    # 시너지 지표
    if entry.jockey_id and entry.trainer_id:
        synergy = await calculate_synergy(
            session, entry.jockey_id, entry.trainer_id, entry.horse_id
        )
        factors.trainer_synergy = min(synergy.best_record_trainer_rate, 100.0)
        factors.horse_jockey_synergy = min(synergy.horse_jockey_synergy_rate, 100.0)

    # Phase 2 신규 요인
    factors.surface_aptitude = await calc_surface_aptitude(
        session, entry.horse_id, race.surface, race.moisture
    )
    factors.class_movement = await calc_class_movement(
        session, entry.horse_id, race.race_level
    )
    factors.running_style_match = await calc_running_style_matching(
        session, entry.horse_id, entry.jockey_id, race.distance
    )
    factors.horse_weight_factor = await calc_horse_weight_factor(
        session, entry.horse_id
    )
    factors.class_trick = await calc_class_trick_score(
        session, entry.horse_id
    )
    factors.jockey_fatigue = await calc_jockey_fatigue(
        session, entry.jockey_id, race.race_date, race.race_number, race.track_id
    )

    # 종합 점수
    total = sum(
        WEIGHTS[k] * getattr(factors, k)
        for k in WEIGHTS
    )

    return total, factors


async def predict_race(session: AsyncSession, race_id: int) -> list[dict]:
    """경주 전체 출주마 예측 실행 + DB 저장"""
    race = await session.get(Race, race_id)
    if not race:
        logger.error(f"Race not found: {race_id}")
        return []

    entries_q = select(RaceEntry).where(RaceEntry.race_id == race_id)
    entries_result = await session.execute(entries_q)
    entries = entries_result.scalars().all()

    if not entries:
        return []

    # 각 출주마 점수 계산
    scores = []
    for entry in entries:
        total, factors = await predict_entry(session, entry, race)
        scores.append({
            "entry": entry,
            "total_score": round(total, 2),
            "factors": factors,
        })

    # 점수 내림차순 정렬 → 예측 순위 부여
    scores.sort(key=lambda x: x["total_score"], reverse=True)

    results = []
    for rank, item in enumerate(scores, 1):
        entry = item["entry"]
        factors_dict = asdict(item["factors"])

        # 기존 예측 삭제 후 재생성
        existing_q = select(Prediction).where(
            and_(
                Prediction.race_id == race_id,
                Prediction.entry_id == entry.id,
                Prediction.is_override == False,
            )
        )
        existing_result = await session.execute(existing_q)
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.total_score = item["total_score"]
            existing.predicted_rank = rank
            existing.confidence = _calc_confidence(item["total_score"], scores)
            existing.factors_json = json.dumps(factors_dict, ensure_ascii=False)
            existing.model_version = MODEL_VERSION
            pred = existing
        else:
            pred = Prediction(
                race_id=race_id,
                entry_id=entry.id,
                total_score=item["total_score"],
                predicted_rank=rank,
                confidence=_calc_confidence(item["total_score"], scores),
                factors_json=json.dumps(factors_dict, ensure_ascii=False),
                model_version=MODEL_VERSION,
            )
            session.add(pred)

        results.append({
            "entry_id": entry.id,
            "horse_number": entry.horse_number,
            "total_score": item["total_score"],
            "predicted_rank": rank,
            "factors": factors_dict,
        })

    await session.commit()
    logger.info(f"Predicted race {race_id}: {len(results)} entries")
    return results


def _calc_confidence(score: float, all_scores: list[dict]) -> float:
    """신뢰도 계산: 점수 분포 기반"""
    if not all_scores:
        return 50.0
    scores = [s["total_score"] for s in all_scores]
    max_s = max(scores)
    min_s = min(scores)
    spread = max_s - min_s
    if spread < 1:
        return 50.0  # 차이가 거의 없으면 낮은 신뢰도
    # 1위와 2위 차이가 클수록 높은 신뢰도
    sorted_scores = sorted(scores, reverse=True)
    if len(sorted_scores) >= 2:
        gap = sorted_scores[0] - sorted_scores[1]
        return min(50 + gap * 5, 95.0)
    return 60.0
