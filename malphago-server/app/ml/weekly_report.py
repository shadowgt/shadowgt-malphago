"""주간 모델 성능 리포트

과거 예측과 실제 결과를 비교하여 모델 성능을 측정한다.
날짜별 정확도 히트맵 데이터, 전체 정확도 추이를 생성한다.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import Prediction
from app.models.race import Race
from app.models.race_entry import RaceEntry

logger = logging.getLogger(__name__)

REPORT_DIR = Path(__file__).parent.parent.parent / "ml_reports"


async def generate_weekly_report(
    session: AsyncSession,
    end_date: date | None = None,
    weeks: int = 1,
) -> dict:
    """주간 모델 성능 리포트를 생성한다.

    Args:
        session: DB session
        end_date: 리포트 종료일 (기본: 오늘)
        weeks: 리포트 기간 (주)

    Returns:
        리포트 데이터
    """
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    # 기간 내 예측이 있는 경주 조회
    preds_q = (
        select(Prediction, Race.race_date, Race.track_id, RaceEntry.ranking)
        .join(Race, Prediction.race_id == Race.id)
        .join(RaceEntry, Prediction.entry_id == RaceEntry.id)
        .where(
            and_(
                Race.race_date >= start_date,
                Race.race_date <= end_date,
                Prediction.is_override == False,
                RaceEntry.ranking.isnot(None),
            )
        )
        .order_by(Race.race_date)
    )
    result = await session.execute(preds_q)
    rows = result.all()

    if not rows:
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_predictions": 0,
            "message": "No predictions with results found",
        }

    # 날짜별 성능 집계
    daily_stats = {}
    total_correct_top3 = 0
    total_correct_win = 0
    total_predictions = 0
    model_versions = set()

    for pred, race_date, track_id, actual_rank in rows:
        date_key = race_date.isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {
                "date": date_key,
                "total": 0,
                "correct_top3": 0,
                "correct_win": 0,
                "races": set(),
            }

        ds = daily_stats[date_key]
        ds["total"] += 1
        ds["races"].add(pred.race_id)
        total_predictions += 1

        # Top3 예측이 실제로 Top3인지
        if pred.predicted_rank <= 3 and actual_rank <= 3:
            ds["correct_top3"] += 1
            total_correct_top3 += 1
        # 1위 예측이 실제 1위인지
        if pred.predicted_rank == 1 and actual_rank == 1:
            ds["correct_win"] += 1
            total_correct_win += 1

        model_versions.add(pred.model_version)

    # 날짜별 정확도 계산
    daily_accuracy = []
    for date_key in sorted(daily_stats.keys()):
        ds = daily_stats[date_key]
        top3_preds = ds["total"]  # 해당 날짜의 모든 예측
        daily_accuracy.append({
            "date": ds["date"],
            "total_predictions": ds["total"],
            "races": len(ds["races"]),
            "top3_accuracy": round(ds["correct_top3"] / ds["total"] * 100, 1) if ds["total"] > 0 else 0,
            "win_accuracy": round(ds["correct_win"] / ds["total"] * 100, 1) if ds["total"] > 0 else 0,
        })

    report = {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "generated_at": datetime.now().isoformat(),
        "total_predictions": total_predictions,
        "model_versions": list(model_versions),
        "overall": {
            "top3_accuracy": round(total_correct_top3 / total_predictions * 100, 1) if total_predictions > 0 else 0,
            "win_accuracy": round(total_correct_win / total_predictions * 100, 1) if total_predictions > 0 else 0,
        },
        "daily_accuracy": daily_accuracy,
    }

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"weekly_{end_date.isoformat()}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Weekly report saved: {report_path}")

    return report


async def get_accuracy_trend(
    session: AsyncSession,
    weeks: int = 8,
) -> list[dict]:
    """최근 N주간 정확도 추이를 반환한다."""
    trends = []
    end = date.today()
    for i in range(weeks):
        week_end = end - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)

        preds_q = (
            select(Prediction, RaceEntry.ranking)
            .join(Race, Prediction.race_id == Race.id)
            .join(RaceEntry, Prediction.entry_id == RaceEntry.id)
            .where(
                and_(
                    Race.race_date >= week_start,
                    Race.race_date <= week_end,
                    Prediction.is_override == False,
                    RaceEntry.ranking.isnot(None),
                )
            )
        )
        result = await session.execute(preds_q)
        rows = result.all()

        if not rows:
            trends.append({
                "week_end": week_end.isoformat(),
                "total": 0,
                "top3_accuracy": 0,
                "win_accuracy": 0,
            })
            continue

        total = len(rows)
        correct_top3 = sum(1 for pred, rank in rows if pred.predicted_rank <= 3 and rank <= 3)
        correct_win = sum(1 for pred, rank in rows if pred.predicted_rank == 1 and rank == 1)

        trends.append({
            "week_end": week_end.isoformat(),
            "total": total,
            "top3_accuracy": round(correct_top3 / total * 100, 1),
            "win_accuracy": round(correct_win / total * 100, 1),
        })

    return list(reversed(trends))
