"""전체 데이터 수집 배치 스크립트

2020-01-01 ~ 2026-04-03 서울+부산 순차 수집.
SQLite 잠금 방지를 위해 하나의 프로세스에서 순차 실행.
"""

import asyncio
import logging
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.kra_api import fetch_race_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def collect_chunk(async_session, start: date, end: date, meets: list[str]):
    """날짜 범위를 순차 수집 (금/토/일만)"""
    from datetime import timedelta

    stats = {"dates": 0, "races": 0, "entries": 0, "errors": 0}
    current = start

    while current <= end:
        if current.weekday() in (4, 5, 6):  # Fri, Sat, Sun
            day_races = 0
            for meet in meets:
                try:
                    async with async_session() as session:
                        async with session.begin():
                            result = await fetch_race_results(session, current, meet)
                    day_races += result["races"]
                    stats["races"] += result["races"]
                    stats["entries"] += result["entries_updated"]
                    stats["errors"] += result["errors"]
                except Exception as e:
                    logger.error(f"Error {current} meet={meet}: {e}")
                    stats["errors"] += 1

                await asyncio.sleep(0.1)

            if day_races > 0:
                stats["dates"] += 1

        current += timedelta(days=1)

    return stats


async def run():
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./malphago_dev.db")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 6개월 단위로 수집 (2022-08-01부터 재개 - 이전 데이터 수집 완료)
    chunks = [
        (date(2022, 8, 1), date(2022, 12, 31)),
        (date(2023, 1, 1), date(2023, 6, 30)),
        (date(2023, 7, 1), date(2023, 12, 31)),
        (date(2024, 1, 7), date(2024, 6, 30)),  # 2024-01-06 이미 수집됨
        (date(2024, 7, 1), date(2024, 12, 31)),
        (date(2025, 1, 1), date(2025, 6, 30)),
        (date(2025, 7, 1), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 4, 3)),
    ]

    meets = ["1", "3"]  # 서울, 부산
    grand_total = {"dates": 0, "races": 0, "entries": 0, "errors": 0}

    for start, end in chunks:
        print(f"\n=== Collecting {start} ~ {end} (meets={meets}) ===")
        stats = await collect_chunk(async_session, start, end, meets)

        for k in grand_total:
            grand_total[k] += stats[k]

        print(f"  Chunk: dates={stats['dates']}, races={stats['races']}, entries={stats['entries']}, errors={stats['errors']}")
        print(f"  Running total: {grand_total}")

    print(f"\n=== ALL DONE ===")
    print(f"Total: {grand_total}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
