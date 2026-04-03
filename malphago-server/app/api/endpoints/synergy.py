from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.synergy import calculate_synergy, calculate_race_synergies
from app.schemas.prediction import SynergySchema, SynergyBriefSchema

router = APIRouter()


@router.get("", response_model=SynergySchema)
async def get_synergy(
    jockey_id: int = Query(..., alias="jockeyId"),
    trainer_id: int = Query(..., alias="trainerId"),
    horse_id: int | None = Query(None, alias="horseId"),
    db: AsyncSession = Depends(get_db),
):
    """시너지 분석 — 기수/조교사/말 조합의 시너지 지표"""
    report = await calculate_synergy(db, jockey_id, trainer_id, horse_id)
    return {
        "jockey_name": report.jockey_name,
        "trainer_name": report.trainer_name,
        "horse_name": report.horse_name,
        "best_record_rate": round(report.best_record_rate, 2),
        "best_record_trainer_rate": round(report.best_record_trainer_rate, 2),
        "high_dividend_record_rate": round(report.high_dividend_record_rate, 2),
        "high_dividend_record_trainer_rate": round(report.high_dividend_record_trainer_rate, 2),
        "horse_jockey_synergy_rate": round(report.horse_jockey_synergy_rate, 2),
        "horse_jockey_total_runs": report.horse_jockey_total_runs,
        "trainer_win_rate": round(report.trainer_win_rate, 2),
        "jockey_total_runs": report.jockey_total_runs,
    }


@router.get("/race/{race_id}", response_model=list[SynergyBriefSchema])
async def get_race_synergies(race_id: int, db: AsyncSession = Depends(get_db)):
    """경주 전체 출주마의 시너지 지표 일괄 조회"""
    reports = await calculate_race_synergies(db, race_id)
    return [
        {
            "jockey_name": r.jockey_name,
            "trainer_name": r.trainer_name,
            "horse_name": r.horse_name,
            "best_record_rate": round(r.best_record_rate, 2),
            "best_record_trainer_rate": round(r.best_record_trainer_rate, 2),
            "high_dividend_record_rate": round(r.high_dividend_record_rate, 2),
            "high_dividend_record_trainer_rate": round(r.high_dividend_record_trainer_rate, 2),
            "horse_jockey_synergy_rate": round(r.horse_jockey_synergy_rate, 2),
            "horse_jockey_total_runs": r.horse_jockey_total_runs,
        }
        for r in reports
    ]
