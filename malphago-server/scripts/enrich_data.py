"""데이터 보강 스크립트

1. race_interval 계산: 각 말의 이전 출전일과의 차이(일)
2. TodayPlayer 데이터 임포트: horse_weight, horse_weight_change, rating
3. horse_number 보강: TodayPlayer에서 추가 매칭

사용법:
  cd malphago-server
  python scripts/enrich_data.py [--sqlite-path PATH]
"""

import argparse
import asyncio
import logging
import re
import sqlite3
import os
import sys
from datetime import date, datetime

from sqlalchemy import select, update, text, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.race import Race
from app.models.race_entry import RaceEntry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SQLITE = "C:/claude/MalPhaGo/sqlite/malphago.db"


def parse_int(s) -> int | None:
    if s is None:
        return None
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None


def parse_float(s) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).strip())
    except (ValueError, TypeError):
        return None


def parse_weight_increase(s: str | None) -> int | None:
    """'1.5' or '-2' or '0' → int"""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


async def calc_race_intervals(session: AsyncSession) -> int:
    """각 entry의 race_interval을 계산한다.

    말(horse_id)별로 출전 이력을 날짜순으로 정렬하고,
    이전 출전일과의 차이(일)를 race_interval로 설정한다.
    """
    logger.info("Calculating race_interval for all entries...")

    # 모든 entry를 horse_id, race_date 순으로 조회
    q = (
        select(RaceEntry.id, RaceEntry.horse_id, Race.race_date)
        .join(Race, RaceEntry.race_id == Race.id)
        .order_by(RaceEntry.horse_id, Race.race_date)
    )
    result = await session.execute(q)
    rows = result.all()

    logger.info(f"Processing {len(rows)} entries for race_interval...")

    # horse_id별로 그룹핑
    horse_entries: dict[int, list[tuple[int, date]]] = {}
    for entry_id, horse_id, race_date in rows:
        if horse_id not in horse_entries:
            horse_entries[horse_id] = []
        horse_entries[horse_id].append((entry_id, race_date))

    logger.info(f"Found {len(horse_entries)} unique horses")

    # 각 말의 출전 이력에서 interval 계산
    updates = []
    for horse_id, entries in horse_entries.items():
        # 이미 날짜순으로 정렬됨
        prev_date = None
        for entry_id, race_date in entries:
            if prev_date is not None:
                interval = (race_date - prev_date).days
                updates.append({"entry_id": entry_id, "interval": interval})
            prev_date = race_date

    # 배치 업데이트
    updated = 0
    batch_size = 500
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        for item in batch:
            await session.execute(
                update(RaceEntry)
                .where(RaceEntry.id == item["entry_id"])
                .values(race_interval=item["interval"])
            )
        await session.flush()
        updated += len(batch)
        if (i + batch_size) % 5000 < batch_size:
            logger.info(f"  Updated {updated}/{len(updates)} entries")

    logger.info(f"race_interval calculated: {updated} entries updated")
    return updated


async def import_today_player(session: AsyncSession, sqlite_path: str) -> dict:
    """TodayPlayer 테이블에서 horse_weight, horse_weight_change, rating을 임포트한다."""
    logger.info(f"Importing TodayPlayer data from {sqlite_path}...")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM TodayPlayer")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    logger.info(f"TodayPlayer: {len(rows)} rows")

    stats = {"matched": 0, "weight_updated": 0, "rating_updated": 0, "number_updated": 0, "skipped": 0}

    # 말 이름 → horse_id 캐시
    horse_result = await session.execute(select(Horse.id, Horse.name))
    horse_map = {name: hid for hid, name in horse_result.all()}

    # 기수 이름 → jockey_id 캐시
    jockey_result = await session.execute(select(Jockey.id, Jockey.name))
    jockey_map = {name: jid for jid, name in jockey_result.all()}

    for row in rows:
        try:
            # raceDate 파싱: "2020-02-22  / 1R"
            raw_date = row.get("raceDate", "")
            m = re.match(r"(\d{4}-\d{2}-\d{2})\s*/\s*(\d+)R", raw_date.strip())
            if not m:
                stats["skipped"] += 1
                continue

            date_str = m.group(1)
            race_number = int(m.group(2))
            race_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            horse_name = row.get("horseName", "").strip()
            if not horse_name:
                stats["skipped"] += 1
                continue

            horse_id = horse_map.get(horse_name)
            if not horse_id:
                stats["skipped"] += 1
                continue

            # race_id 찾기: race_date + race_number로 매칭
            # track은 raceName에서 추출
            track_name = row.get("raceName", "").strip()
            track_code_map = {"서울경마": 1, "부산경마": 2, "제주경마": 3}
            track_id = track_code_map.get(track_name)
            if not track_id:
                stats["skipped"] += 1
                continue

            race_q = select(Race.id).where(
                Race.track_id == track_id,
                Race.race_date == race_date,
                Race.race_number == race_number,
            )
            race_result = await session.execute(race_q)
            race_row = race_result.first()
            if not race_row:
                stats["skipped"] += 1
                continue
            race_id = race_row[0]

            # entry 매칭: race_id + horse_id
            entry_q = select(RaceEntry).where(
                RaceEntry.race_id == race_id,
                RaceEntry.horse_id == horse_id,
            )
            entry_result = await session.execute(entry_q)
            entry = entry_result.scalar_one_or_none()
            if not entry:
                stats["skipped"] += 1
                continue

            stats["matched"] += 1

            # weight: "56.5" → horse_weight (kg, as int)
            weight = parse_float(row.get("weight"))
            if weight and not entry.horse_weight:
                entry.horse_weight = int(weight)
                stats["weight_updated"] += 1

            # increase: "1.5" → horse_weight_change
            increase = parse_weight_increase(row.get("increase"))
            if increase is not None and entry.horse_weight_change is None:
                entry.horse_weight_change = increase
                stats["weight_updated"] += 1

            # rating
            rating = parse_int(row.get("rating"))
            if rating and not entry.rating:
                entry.rating = rating
                stats["rating_updated"] += 1

            # horse_number
            number = parse_int(row.get("number"))
            if number and not entry.horse_number:
                entry.horse_number = number
                stats["number_updated"] += 1

        except Exception as e:
            logger.warning(f"TodayPlayer row skip: {e}")
            stats["skipped"] += 1

    await session.flush()
    logger.info(f"TodayPlayer import: {stats}")
    return stats


async def print_data_quality(session: AsyncSession):
    """데이터 품질 리포트 출력"""
    total = (await session.execute(select(func.count(RaceEntry.id)))).scalar()

    print("\n=== Data Quality Report ===")
    print(f"Total entries: {total}")

    fields = [
        "horse_number", "horse_weight", "horse_weight_change",
        "race_interval", "odds_win", "odds_place", "rating",
        "favor_ranking", "ranking",
    ]

    for field in fields:
        col = getattr(RaceEntry, field)
        count = (await session.execute(
            select(func.count(RaceEntry.id)).where(col.isnot(None))
        )).scalar()
        pct = count / total * 100 if total else 0
        print(f"  {field:25s}: {count:>6}/{total}  ({pct:5.1f}%)")

    # Race fields
    race_total = (await session.execute(select(func.count(Race.id)))).scalar()
    print(f"\nTotal races: {race_total}")
    for field in ["surface", "weather", "moisture"]:
        col = getattr(Race, field)
        count = (await session.execute(
            select(func.count(Race.id)).where(col.isnot(None))
        )).scalar()
        pct = count / race_total * 100 if race_total else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {field:25s}: {count:>6}/{race_total}  ({pct:5.1f}%) {bar}")


async def run(sqlite_path: str, db_url: str):
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            # 1. race_interval 계산
            interval_count = await calc_race_intervals(session)

        async with session.begin():
            # 2. TodayPlayer 임포트
            tp_stats = await import_today_player(session, sqlite_path)

        async with session.begin():
            # 3. 데이터 품질 리포트
            await print_data_quality(session)

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="데이터 보강")
    parser.add_argument("--sqlite-path", default=DEFAULT_SQLITE)
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./malphago_dev.db"),
    )
    args = parser.parse_args()

    asyncio.run(run(args.sqlite_path, args.db_url))


if __name__ == "__main__":
    main()
