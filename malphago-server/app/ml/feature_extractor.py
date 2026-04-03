"""ML 피처 추출기

DB의 과거 경주 데이터에서 학습용 피처 매트릭스를 생성한다.
기존 prediction.py의 15개 요인을 피처로 사용하되,
추가 원시 피처(배당률, 마체중, 출전간격 등)도 포함한다.

타겟: 3위 이내 입상 여부 (이진 분류)
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming
from app.services.prediction import predict_entry

logger = logging.getLogger(__name__)


FEATURE_COLUMNS = [
    # 15 existing prediction factors
    "horse_win_rate",
    "distance_aptitude",
    "surface_aptitude",
    "form_index",
    "class_movement",
    "gate_position",
    "jockey_win_rate",
    "jockey_track_spec",
    "jockey_fatigue",
    "trainer_synergy",
    "horse_jockey_synergy",
    "rest_period",
    "running_style_match",
    "horse_weight_factor",
    "class_trick",
    # Raw features (additional)
    "odds_win",
    "odds_place",
    "horse_weight",
    "horse_weight_change",
    "race_interval",
    "horse_number",
    "total_entries",
    "rating",
    "distance",
    "favor_ranking",
]

TARGET_COL = "is_top3"


async def extract_race_features(
    session: AsyncSession,
    race: Race,
    entries: list[RaceEntry],
) -> list[dict]:
    """단일 경주의 모든 출주마에 대한 피처를 추출한다.

    Returns:
        list of dicts, each containing features + target
    """
    rows = []
    for entry in entries:
        if entry.ranking is None:
            continue

        try:
            _, factors = await predict_entry(session, entry, race)
        except Exception as e:
            logger.warning(f"Factor calc failed for entry {entry.id}: {e}")
            continue

        row = {
            # Prediction factors (0-100)
            "horse_win_rate": factors.horse_win_rate,
            "distance_aptitude": factors.distance_aptitude,
            "surface_aptitude": factors.surface_aptitude,
            "form_index": factors.form_index,
            "class_movement": factors.class_movement,
            "gate_position": factors.gate_position,
            "jockey_win_rate": factors.jockey_win_rate,
            "jockey_track_spec": factors.jockey_track_spec,
            "jockey_fatigue": factors.jockey_fatigue,
            "trainer_synergy": factors.trainer_synergy,
            "horse_jockey_synergy": factors.horse_jockey_synergy,
            "rest_period": factors.rest_period,
            "running_style_match": factors.running_style_match,
            "horse_weight_factor": factors.horse_weight_factor,
            "class_trick": factors.class_trick,
            # Raw features
            "odds_win": float(entry.odds_win) if entry.odds_win else np.nan,
            "odds_place": float(entry.odds_place) if entry.odds_place else np.nan,
            "horse_weight": entry.horse_weight or np.nan,
            "horse_weight_change": entry.horse_weight_change or np.nan,
            "race_interval": entry.race_interval or np.nan,
            "horse_number": entry.horse_number or np.nan,
            "total_entries": race.total_entries or np.nan,
            "rating": entry.rating or np.nan,
            "distance": race.distance or np.nan,
            "favor_ranking": entry.favor_ranking or np.nan,
            # Meta (not used as features)
            "race_id": race.id,
            "entry_id": entry.id,
            "race_date": race.race_date.isoformat() if race.race_date else None,
            "track_id": race.track_id,
            # Target
            "ranking": entry.ranking,
            "is_top3": 1 if entry.ranking <= 3 else 0,
            "is_win": 1 if entry.ranking == 1 else 0,
        }
        rows.append(row)

    return rows


async def build_dataset(
    session: AsyncSession,
    min_entries: int = 5,
) -> pd.DataFrame:
    """전체 과거 경주 데이터에서 학습 데이터셋을 구축한다.

    Args:
        session: DB session
        min_entries: 최소 출주 두수 (너무 적은 경주는 제외)

    Returns:
        DataFrame with features + targets
    """
    races_q = (
        select(Race)
        .where(Race.race_time.isnot(None))  # 결과가 있는 경주만
        .order_by(Race.race_date)
    )
    races_result = await session.execute(races_q)
    races = races_result.scalars().all()

    logger.info(f"Building dataset from {len(races)} completed races")

    all_rows = []
    for i, race in enumerate(races):
        entries_q = (
            select(RaceEntry)
            .where(RaceEntry.race_id == race.id)
            .options(selectinload(RaceEntry.race))
        )
        entries_result = await session.execute(entries_q)
        entries = entries_result.scalars().all()

        if len(entries) < min_entries:
            continue

        rows = await extract_race_features(session, race, entries)
        all_rows.extend(rows)

        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(races)} races, {len(all_rows)} samples")

    df = pd.DataFrame(all_rows)
    logger.info(
        f"Dataset built: {len(df)} samples from {df['race_id'].nunique()} races"
    )
    return df


def prepare_xy(
    df: pd.DataFrame,
    target: str = TARGET_COL,
) -> tuple[pd.DataFrame, pd.Series]:
    """DataFrame에서 X (features), y (target)을 분리한다."""
    meta_cols = ["race_id", "entry_id", "race_date", "track_id", "ranking", "is_top3", "is_win"]
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[feature_cols].copy()
    y = df[target].copy()

    # NaN 처리: 중앙값으로 대체
    for col in X.columns:
        if X[col].isna().any():
            X[col] = X[col].fillna(X[col].median())

    return X, y
