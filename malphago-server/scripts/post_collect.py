"""수집 후 후처리 + ML 학습 파이프라인

1. race_interval 재계산
2. 데이터 품질 리포트
3. ML 데이터셋 생성 + 모델 학습
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run():
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./malphago_dev.db")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Step 1: race_interval 재계산
    print("=" * 60)
    print("Step 1: Recalculating race_interval...")
    print("=" * 60)
    from scripts.enrich_data import calc_race_intervals, print_data_quality

    async with async_session() as session:
        async with session.begin():
            count = await calc_race_intervals(session)
    print(f"  Updated {count} entries")

    # Step 2: 데이터 품질 리포트
    print("\n" + "=" * 60)
    print("Step 2: Data Quality Report")
    print("=" * 60)
    async with async_session() as session:
        async with session.begin():
            await print_data_quality(session)

    await engine.dispose()

    # Step 3: ML pipeline
    print("\n" + "=" * 60)
    print("Step 3: ML Pipeline (dataset → compare → train)")
    print("=" * 60)
    from app.ml.train_cli import run_all
    await run_all()


if __name__ == "__main__":
    asyncio.run(run())
