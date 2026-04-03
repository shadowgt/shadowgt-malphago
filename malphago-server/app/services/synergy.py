"""시너지 분석 서비스

기존 MalPhaGo Form1.cs:654-691 기반 4개 지표를 Python으로 이식 + 신규 지표 추가.

기존 4개 지표:
1. bestRecordRate: 기수의 3위 이내 입상률 (%)
2. bestRecordTrainerRate: 기수가 해당 조교사와 함께한 경우의 입상률 (%)
3. highDividendRecordRate: 이변 입상률 (인기순위 4위 이하에서 3위 이내) (%)
4. highDividendRecordTrainerRate: 해당 조교사와의 이변 입상률 (%)

신규 지표:
5. horseJockeySynergyRate: 말-기수 직접 조합 입상률
6. trainerWinRate: 조교사 전체 승률
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.horse import Horse

logger = logging.getLogger(__name__)


@dataclass
class SynergyReport:
    """시너지 분석 결과"""
    jockey_name: str = ""
    trainer_name: str = ""
    horse_name: str = ""

    # 기존 4개 지표 (Form1.cs 이식)
    best_record_rate: float = 0.0              # 기수 3위이내 입상률
    best_record_trainer_rate: float = 0.0      # 기수-조교사 조합 입상률
    high_dividend_record_rate: float = 0.0     # 이변 입상률
    high_dividend_record_trainer_rate: float = 0.0  # 조교사 이변 입상률

    # 신규 지표
    horse_jockey_synergy_rate: float = 0.0     # 말-기수 직접 조합 입상률
    horse_jockey_total_runs: int = 0           # 말-기수 총 출전 횟수
    trainer_win_rate: float = 0.0              # 조교사 전체 승률

    # 통계 기반 데이터
    jockey_total_runs: int = 0                 # 기수 총 출전 횟수
    jockey_top3_count: int = 0                 # 기수 3위이내 횟수
    jockey_trainer_runs: int = 0               # 기수-조교사 조합 출전
    jockey_trainer_top3: int = 0               # 기수-조교사 조합 3위이내


async def calculate_synergy(
    session: AsyncSession,
    jockey_id: int,
    trainer_id: int,
    horse_id: int | None = None,
) -> SynergyReport:
    """시너지 지표 계산

    Args:
        session: DB 세션
        jockey_id: 기수 ID
        trainer_id: 조교사 ID
        horse_id: 말 ID (신규 지표용, optional)

    Returns:
        SynergyReport
    """
    report = SynergyReport()

    # 기수 정보
    jockey = await session.get(Jockey, jockey_id)
    trainer = await session.get(Trainer, trainer_id)
    if jockey:
        report.jockey_name = jockey.name
    if trainer:
        report.trainer_name = trainer.name

    # ─── 1. bestRecordRate: 기수의 3위이내 입상률 ───
    # 기수의 전체 출전 기록 조회
    jockey_entries_q = select(RaceEntry).where(RaceEntry.jockey_id == jockey_id)
    jockey_entries_result = await session.execute(jockey_entries_q)
    jockey_entries = jockey_entries_result.scalars().all()

    report.jockey_total_runs = len(jockey_entries)

    if report.jockey_total_runs > 0:
        # ranking이 있고 3이하인 기록
        top3 = [e for e in jockey_entries if e.ranking is not None and e.ranking <= 3]
        report.jockey_top3_count = len(top3)
        report.best_record_rate = (len(top3) / report.jockey_total_runs) * 100

        # ─── 2. bestRecordTrainerRate: 기수-조교사 입상률 ───
        # top3 중 해당 조교사와 함께한 기록
        top3_with_trainer = [e for e in top3 if e.trainer_id == trainer_id]
        report.jockey_trainer_top3 = len(top3_with_trainer)
        if len(top3) > 0:
            report.best_record_trainer_rate = (len(top3_with_trainer) / len(top3)) * 100

        # 기수-조교사 조합 총 출전
        with_trainer = [e for e in jockey_entries if e.trainer_id == trainer_id]
        report.jockey_trainer_runs = len(with_trainer)

        # ─── 3. highDividendRecordRate: 이변 입상률 ───
        # ranking <= 3 이고 favor_ranking > 3 (인기 4위 이하에서 3위이내 입상)
        high_dividend = [
            e for e in jockey_entries
            if e.ranking is not None and e.ranking <= 3
            and e.favor_ranking is not None and e.favor_ranking > 3
        ]
        if report.jockey_total_runs > 0:
            report.high_dividend_record_rate = (len(high_dividend) / report.jockey_total_runs) * 100

        # ─── 4. highDividendRecordTrainerRate: 조교사 이변 입상률 ───
        if len(high_dividend) > 0:
            high_dividend_with_trainer = [
                e for e in high_dividend if e.trainer_id == trainer_id
            ]
            report.high_dividend_record_trainer_rate = (
                len(high_dividend_with_trainer) / len(high_dividend)
            ) * 100

    # ─── 5. horseJockeySynergyRate: 말-기수 직접 조합 (신규) ───
    if horse_id:
        horse = await session.get(Horse, horse_id)
        if horse:
            report.horse_name = horse.name

        horse_jockey_q = select(RaceEntry).where(
            and_(
                RaceEntry.horse_id == horse_id,
                RaceEntry.jockey_id == jockey_id,
            )
        )
        hj_result = await session.execute(horse_jockey_q)
        hj_entries = hj_result.scalars().all()
        report.horse_jockey_total_runs = len(hj_entries)

        if len(hj_entries) > 0:
            hj_top3 = [e for e in hj_entries if e.ranking is not None and e.ranking <= 3]
            report.horse_jockey_synergy_rate = (len(hj_top3) / len(hj_entries)) * 100

    # ─── 6. trainerWinRate: 조교사 승률 ───
    trainer_entries_q = select(RaceEntry).where(RaceEntry.trainer_id == trainer_id)
    trainer_result = await session.execute(trainer_entries_q)
    trainer_entries = trainer_result.scalars().all()

    if len(trainer_entries) > 0:
        trainer_wins = [e for e in trainer_entries if e.ranking == 1]
        report.trainer_win_rate = (len(trainer_wins) / len(trainer_entries)) * 100

    return report


async def calculate_race_synergies(
    session: AsyncSession, race_id: int
) -> list[SynergyReport]:
    """경주 전체 출주마의 시너지 지표 일괄 계산"""
    entries_q = select(RaceEntry).where(RaceEntry.race_id == race_id)
    entries_result = await session.execute(entries_q)
    entries = entries_result.scalars().all()

    reports = []
    for entry in entries:
        if not entry.jockey_id or not entry.trainer_id:
            continue
        report = await calculate_synergy(
            session,
            jockey_id=entry.jockey_id,
            trainer_id=entry.trainer_id,
            horse_id=entry.horse_id,
        )
        reports.append(report)

    return reports
