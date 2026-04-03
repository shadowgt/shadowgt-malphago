"""data.go.kr KRA API를 통한 경주 데이터 수집 CLI

사용법:
  # 특정 날짜 수집
  python scripts/collect_kra.py --date 2024-01-06

  # 날짜 범위 수집
  python scripts/collect_kra.py --start 2021-09-01 --end 2024-12-31

  # 특정 경마장만
  python scripts/collect_kra.py --start 2024-01-01 --end 2024-03-31 --meet 1

사전 요구: .env에 DATA_GO_KR_SERVICE_KEY 설정
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.kra_api import collect_date_range, fetch_race_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run(args):
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./malphago_dev.db")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    meets = [args.meet] if args.meet else ["1", "3"]  # 서울, 부산

    async with async_session() as session:
        if args.date:
            # 단일 날짜
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            async with session.begin():
                for meet in meets:
                    stats = await fetch_race_results(session, target_date, meet)
                    print(f"Date={target_date}, Meet={meet}: {stats}")
        else:
            # 날짜 범위
            start = datetime.strptime(args.start, "%Y-%m-%d").date()
            end = datetime.strptime(args.end, "%Y-%m-%d").date()
            print(f"Collecting: {start} ~ {end}, meets={meets}")

            async with session.begin():
                stats = await collect_date_range(session, start, end, meets)
                print(f"\n=== Collection Complete ===")
                print(f"Dates: {stats['dates']}")
                print(f"Races: {stats['races']}")
                print(f"Entries: {stats['entries']}")
                print(f"Errors: {stats['errors']}")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="KRA 공공데이터 API 수집")
    parser.add_argument("--date", help="단일 날짜 (YYYY-MM-DD)")
    parser.add_argument("--start", help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end", help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument("--meet", help="경마장 코드 (1=서울, 3=부산)")
    args = parser.parse_args()

    if not args.date and not (args.start and args.end):
        parser.error("--date 또는 --start + --end 필요")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
