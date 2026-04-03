"""분석 API - 각질 분류 등"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.running_style import (
    analyze_running_style,
    analyze_race_running_styles,
    RunningStyleAnalysis,
)

router = APIRouter()


@router.get("/horse/{horse_id}/running-style")
async def get_horse_running_style(
    horse_id: int,
    recent_n: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """말의 각질(주행 스타일) 분석"""
    analysis = await analyze_running_style(db, horse_id, recent_n)
    return {
        "horse_id": horse_id,
        "style": analysis.style.value,
        "avg_corner_position": analysis.avg_corner_position,
        "early_speed_score": analysis.early_speed_score,
        "late_kick_score": analysis.late_kick_score,
        "acceleration_ratio": analysis.acceleration_ratio,
        "consistency": analysis.consistency,
        "sample_count": analysis.sample_count,
    }


@router.get("/race/{race_id}/running-styles")
async def get_race_running_styles(
    race_id: int,
    db: AsyncSession = Depends(get_db),
):
    """경주 전체 출주마의 각질 일괄 분석"""
    analyses = await analyze_race_running_styles(db, race_id)
    return [
        {
            "horse_id": horse_id,
            "style": a.style.value,
            "avg_corner_position": a.avg_corner_position,
            "early_speed_score": a.early_speed_score,
            "late_kick_score": a.late_kick_score,
            "acceleration_ratio": a.acceleration_ratio,
            "consistency": a.consistency,
            "sample_count": a.sample_count,
        }
        for horse_id, a in analyses.items()
    ]
