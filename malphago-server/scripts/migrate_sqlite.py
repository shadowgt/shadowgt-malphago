"""기존 malphago.db (SQLite) → PostgreSQL 마이그레이션 스크립트

old schema:
  Record        → horse, jockey, trainer (마스터 추출) + Race + RaceEntry
  RecordOffical → RaceEntry(ranking) + RaceTiming (코너, 구간기록)
  TodayPlayer   → 참고용 (현재 출주표, 마이그레이션 대상 아님)

사용법:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/db \
  python scripts/migrate_sqlite.py [--sqlite-path PATH] [--batch-size N] [--dry-run]
"""

import argparse
import asyncio
import logging
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.base import Base
from app.models.track import Track
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SQLITE = "C:/claude/MalPhaGo/sqlite/malphago.db"

# 트랙 코드 매핑
TRACK_MAP = {
    "서울경마": ("S", "서울", "Seoul"),
    "부산경마": ("B", "부산", "Busan"),
    "제주경마": ("J", "제주", "Jeju"),
}


def parse_race_date_round(raw: str) -> tuple[str, int, str] | None:
    """'2020-02-22 / 1R' 또는 '2020-02-22  / 1R' → (date_str, round_num, raw_key)
    RecordOffical의 _key도 동일 형식.
    """
    m = re.match(r"(\d{4}[-/]\d{2}[-/]\d{2})\s*/\s*(\d+)R", raw.strip())
    if not m:
        return None
    date_str = m.group(1).replace("/", "-")
    round_num = int(m.group(2))
    return date_str, round_num, raw.strip()


def parse_date(s: str) -> date | None:
    """날짜 문자열 파싱"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None


def parse_float(s: str | None) -> float | None:
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_time_to_seconds(s: str | None) -> str | None:
    """'0:36.7' or '1:24.3' → 그대로 문자열 반환 (record_full용)"""
    if not s or not str(s).strip():
        return None
    return str(s).strip()


def parse_corners(corner_str: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    """'6-   -   - 6- 5- 4- 1' → (c1, c2, c3, c4)
    코너 수는 경주 거리에 따라 다름. 마지막 4개 숫자가 코너 1~4.
    빈 값('-' 또는 공백)은 None.
    """
    if not corner_str:
        return None, None, None, None

    # 숫자만 추출
    nums = re.findall(r"\d+", corner_str)
    if not nums:
        return None, None, None, None

    # 마지막 4개를 코너 1~4로 (짧은 거리는 코너가 적을 수 있음)
    if len(nums) >= 4:
        return nums[-4], nums[-3], nums[-2], nums[-1]
    elif len(nums) == 3:
        return None, nums[0], nums[1], nums[2]
    elif len(nums) == 2:
        return None, None, nums[0], nums[1]
    elif len(nums) == 1:
        return None, None, None, nums[0]
    return None, None, None, None


def parse_prize(s: str | None) -> int | None:
    """'13,750,000원' → 13750000"""
    if not s:
        return None
    s = str(s).strip()
    m = re.sub(r"[^\d]", "", s)
    return int(m) if m else None


def parse_distance(s: str | None) -> int | None:
    """'1000M' or '1200' → 1000 or 1200"""
    if not s:
        return None
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else None


class Migrator:
    def __init__(self, sqlite_path: str, db_url: str, batch_size: int = 500, dry_run: bool = False):
        self.sqlite_path = sqlite_path
        self.db_url = db_url
        self.batch_size = batch_size
        self.dry_run = dry_run

        # 캐시: name → id
        self.horse_cache: dict[str, int] = {}
        self.jockey_cache: dict[str, int] = {}
        self.trainer_cache: dict[str, int] = {}
        self.track_cache: dict[str, int] = {}  # code → id
        # race 캐시: (track_id, date_str, race_number) → race_id
        self.race_cache: dict[tuple[int, str, int], int] = {}
        # entry 캐시: (race_id, horse_id) → entry_id (중복 방지)
        self.entry_cache: set[tuple[int, int]] = set()

        self.stats = {
            "horses": 0, "jockeys": 0, "trainers": 0, "tracks": 0,
            "races": 0, "entries": 0, "timings": 0,
            "skipped_records": 0, "skipped_offical": 0,
        }

    def read_sqlite(self) -> tuple[list, list]:
        """SQLite에서 Record, RecordOffical 읽기"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row

        cur = conn.execute("SELECT * FROM Record")
        records = [dict(row) for row in cur.fetchall()]
        logger.info(f"Record 테이블: {len(records)}행")

        cur = conn.execute("SELECT * FROM RecordOffical")
        officals = [dict(row) for row in cur.fetchall()]
        logger.info(f"RecordOffical 테이블: {len(officals)}행")

        conn.close()
        return records, officals

    async def ensure_tracks(self, session: AsyncSession):
        """트랙 마스터 데이터 생성"""
        for name, (code, name_kr, name_en) in TRACK_MAP.items():
            result = await session.execute(select(Track).where(Track.code == code))
            track = result.scalar_one_or_none()
            if not track:
                track = Track(code=code, name=name_kr, name_en=name_en)
                session.add(track)
                await session.flush()
                self.stats["tracks"] += 1
            self.track_cache[code] = track.id
        await session.commit()
        logger.info(f"트랙: {self.track_cache}")

    async def get_or_create_horse(self, session: AsyncSession, name: str, **kwargs) -> int:
        name = name.strip()
        if name in self.horse_cache:
            return self.horse_cache[name]
        result = await session.execute(select(Horse).where(Horse.name == name))
        horse = result.scalar_one_or_none()
        if not horse:
            horse = Horse(name=name, **kwargs)
            session.add(horse)
            await session.flush()
            self.stats["horses"] += 1
        self.horse_cache[name] = horse.id
        return horse.id

    async def get_or_create_jockey(self, session: AsyncSession, name: str) -> int:
        name = name.strip()
        if name in self.jockey_cache:
            return self.jockey_cache[name]
        result = await session.execute(select(Jockey).where(Jockey.name == name))
        jockey = result.scalar_one_or_none()
        if not jockey:
            jockey = Jockey(name=name)
            session.add(jockey)
            await session.flush()
            self.stats["jockeys"] += 1
        self.jockey_cache[name] = jockey.id
        return jockey.id

    async def get_or_create_trainer(self, session: AsyncSession, name: str) -> int:
        name = name.strip()
        if name in self.trainer_cache:
            return self.trainer_cache[name]
        result = await session.execute(select(Trainer).where(Trainer.name == name))
        trainer = result.scalar_one_or_none()
        if not trainer:
            trainer = Trainer(name=name)
            session.add(trainer)
            await session.flush()
            self.stats["trainers"] += 1
        self.trainer_cache[name] = trainer.id
        return trainer.id

    async def get_or_create_race(
        self, session: AsyncSession,
        track_id: int, race_date: date, race_number: int,
        **kwargs,
    ) -> int:
        cache_key = (track_id, str(race_date), race_number)
        if cache_key in self.race_cache:
            return self.race_cache[cache_key]
        result = await session.execute(
            select(Race).where(
                Race.track_id == track_id,
                Race.race_date == race_date,
                Race.race_number == race_number,
            )
        )
        race = result.scalar_one_or_none()
        if not race:
            race = Race(
                track_id=track_id,
                race_date=race_date,
                race_number=race_number,
                **kwargs,
            )
            session.add(race)
            await session.flush()
            self.stats["races"] += 1
        else:
            # 기존 race에 추가 정보 업데이트
            for k, v in kwargs.items():
                if v is not None and getattr(race, k) is None:
                    setattr(race, k, v)
        self.race_cache[cache_key] = race.id
        return race.id

    async def migrate_records(self, session: AsyncSession, records: list):
        """Record 테이블 마이그레이션 → Horse, Jockey, Trainer, Race, RaceEntry"""
        logger.info(f"Record 마이그레이션 시작 ({len(records)}행)...")

        for i, row in enumerate(records):
            try:
                # raceDate 파싱: '2020-02-15 / 9R| 디케이마루|...'
                raw_date = row["raceDate"]
                parsed = parse_race_date_round(raw_date)
                if not parsed:
                    self.stats["skipped_records"] += 1
                    continue

                date_str, race_number, _ = parsed
                race_date = parse_date(date_str)
                if not race_date:
                    self.stats["skipped_records"] += 1
                    continue

                horse_name = row.get("horseName", "").strip()
                jockey_name = row.get("playerName", "").strip()
                trainer_name = row.get("trainer", "").strip()
                track_name = row.get("raceName", "").strip()

                if not horse_name or not track_name:
                    self.stats["skipped_records"] += 1
                    continue

                # 트랙 매핑
                track_info = TRACK_MAP.get(track_name)
                if not track_info:
                    self.stats["skipped_records"] += 1
                    continue
                track_id = self.track_cache[track_info[0]]

                # 마스터 생성
                owner = row.get("horseOwner", "").strip() or None
                horse_id = await self.get_or_create_horse(session, horse_name, owner=owner)
                jockey_id = await self.get_or_create_jockey(session, jockey_name) if jockey_name else None
                trainer_id = await self.get_or_create_trainer(session, trainer_name) if trainer_name else None

                # Race 생성
                distance = parse_distance(row.get("raceDistance"))
                race_id = await self.get_or_create_race(
                    session, track_id, race_date, race_number,
                    race_name=row.get("raceName"),
                    race_level=row.get("horseLevel", "").strip() or None,
                    distance=distance,
                    total_entries=parse_int(row.get("totalNumber")),
                )

                # Entry 생성 (중복 방지)
                entry_key = (race_id, horse_id)
                if entry_key in self.entry_cache:
                    continue
                self.entry_cache.add(entry_key)

                entry = RaceEntry(
                    race_id=race_id,
                    horse_id=horse_id,
                    jockey_id=jockey_id,
                    trainer_id=trainer_id,
                    ranking=parse_int(row.get("ranking")),
                    favor_ranking=parse_int(row.get("favorRanking")),
                )
                session.add(entry)
                self.stats["entries"] += 1

                # 배치 flush
                if (i + 1) % self.batch_size == 0:
                    await session.flush()
                    logger.info(f"  Record: {i+1}/{len(records)} 처리됨")

            except Exception as e:
                logger.warning(f"Record 행 {i} 스킵: {e}")
                self.stats["skipped_records"] += 1

        await session.flush()
        logger.info(f"Record 마이그레이션 완료: {self.stats['entries']}개 엔트리")

    async def migrate_officals(self, session: AsyncSession, officals: list):
        """RecordOffical 마이그레이션 → Race 보강 + RaceTiming"""
        logger.info(f"RecordOffical 마이그레이션 시작 ({len(officals)}행)...")

        for i, row in enumerate(officals):
            try:
                raw_key = row.get("_key", "")
                parsed = parse_race_date_round(raw_key)
                if not parsed:
                    self.stats["skipped_offical"] += 1
                    continue

                date_str, race_number, _ = parsed
                race_date = parse_date(date_str)
                if not race_date:
                    self.stats["skipped_offical"] += 1
                    continue

                track_name = row.get("raceName", "").strip()
                track_info = TRACK_MAP.get(track_name)
                if not track_info:
                    self.stats["skipped_offical"] += 1
                    continue
                track_id = self.track_cache[track_info[0]]

                # Race 조회/생성 + 정보 보강
                distance = parse_distance(row.get("raceDistance"))
                race_id = await self.get_or_create_race(
                    session, track_id, race_date, race_number,
                    race_level=row.get("raceLevel", "").strip() or None,
                    distance=distance,
                    weather=row.get("weather", "").strip() or None,
                    moisture=row.get("waterPersent", "").strip() or None,
                    race_time=row.get("raceTime", "").strip() or None,
                    prize_1st=parse_prize(row.get("prizeMoney_1st")),
                    prize_2nd=parse_prize(row.get("prizeMoney_2nd")),
                    prize_3rd=parse_prize(row.get("prizeMoney_3rd")),
                    prize_4th=parse_prize(row.get("prizeMoney_4th")),
                    prize_5th=parse_prize(row.get("prizeMoney_5th")),
                )

                # 기수명으로 Entry 매칭
                jockey_name = row.get("playerName", "").strip()
                horse_number = parse_int(row.get("horseNumber"))

                if not jockey_name:
                    self.stats["skipped_offical"] += 1
                    continue

                # race_id + horse_number로 entry 찾기 (가장 정확)
                entry = None
                if horse_number:
                    result = await session.execute(
                        select(RaceEntry).where(
                            RaceEntry.race_id == race_id,
                            RaceEntry.horse_number == horse_number,
                        )
                    )
                    entry = result.scalar_one_or_none()

                if not entry:
                    # jockey_id로 찾기
                    jockey_id = self.jockey_cache.get(jockey_name)
                    if jockey_id:
                        result = await session.execute(
                            select(RaceEntry).where(
                                RaceEntry.race_id == race_id,
                                RaceEntry.jockey_id == jockey_id,
                            )
                        )
                        entry = result.scalar_one_or_none()

                if not entry:
                    # RecordOffical에만 있는 기록 → Entry 새로 생성
                    # 기수는 있지만 말 이름이 없음 → 기수명으로 Entry 식별 불가
                    # horse_number가 있으면 Entry 생성 가능
                    self.stats["skipped_offical"] += 1
                    continue

                # Entry에 horse_number 및 ranking 업데이트
                if horse_number and not entry.horse_number:
                    entry.horse_number = horse_number
                ranking = parse_int(row.get("ranking"))
                if ranking and not entry.ranking:
                    entry.ranking = ranking

                # Timing 생성 (이미 있으면 스킵)
                result = await session.execute(
                    select(RaceTiming).where(RaceTiming.entry_id == entry.id)
                )
                existing_timing = result.scalar_one_or_none()
                if existing_timing:
                    continue

                # 코너 순위 파싱
                record_full_raw = row.get("recordFull", "")
                c1, c2, c3, c4 = parse_corners(record_full_raw)

                timing = RaceTiming(
                    entry_id=entry.id,
                    corner_1=c1,
                    corner_2=c2,
                    corner_3=c3,
                    corner_4=c4,
                    s1f=parse_float(row.get("S_1F")),
                    g3f=parse_float(row.get("cornerG_3F")),
                    g1f=parse_float(row.get("cornerG_1F")),
                    record_full=parse_time_to_seconds(row.get("Final")),
                    split_10_8f=parse_float(row.get("_10_8F")),
                    split_8_6f=parse_float(row.get("_8_6F")),
                    split_6_4f=parse_float(row.get("_6_4F")),
                    split_4_2f=parse_float(row.get("_4_2F")),
                    split_2f_g=parse_float(row.get("_2F_G")),
                    split_3f_g=parse_float(row.get("_3F_G")),
                    split_1f_g=parse_float(row.get("_1F_G")),
                    final_time=parse_time_to_seconds(row.get("Final")),
                )
                session.add(timing)
                self.stats["timings"] += 1

                if (i + 1) % self.batch_size == 0:
                    await session.flush()
                    logger.info(f"  RecordOffical: {i+1}/{len(officals)} 처리됨")

            except Exception as e:
                logger.warning(f"RecordOffical 행 {i} 스킵: {e}")
                self.stats["skipped_offical"] += 1

        await session.flush()
        logger.info(f"RecordOffical 마이그레이션 완료: {self.stats['timings']}개 타이밍")

    async def run(self):
        logger.info(f"=== 마이그레이션 시작 ===")
        logger.info(f"SQLite: {self.sqlite_path}")
        logger.info(f"PostgreSQL: {self.db_url.split('@')[-1] if '@' in self.db_url else '(hidden)'}")
        logger.info(f"Dry run: {self.dry_run}")

        # SQLite 읽기
        records, officals = self.read_sqlite()

        # PostgreSQL 연결
        engine = create_async_engine(self.db_url, echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            async with session.begin():
                await self.ensure_tracks(session)

            # Record 먼저 (마스터 데이터 + Entry 생성)
            async with session.begin():
                await self.migrate_records(session, records)

            # RecordOffical (Timing 데이터 + Entry 보강)
            async with session.begin():
                await self.migrate_officals(session, officals)

            if self.dry_run:
                logger.info("Dry run → 롤백")
                await session.rollback()
            else:
                logger.info("커밋 중...")

        await engine.dispose()

        logger.info("=== 마이그레이션 완료 ===")
        for k, v in self.stats.items():
            logger.info(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="malphago.db → PostgreSQL 마이그레이션")
    parser.add_argument(
        "--sqlite-path", default=DEFAULT_SQLITE,
        help=f"기존 SQLite DB 경로 (기본: {DEFAULT_SQLITE})",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL URL (기본: DATABASE_URL 환경변수)",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="실제 커밋하지 않고 테스트")
    args = parser.parse_args()

    if not args.db_url:
        print("ERROR: DATABASE_URL 환경변수 또는 --db-url 파라미터 필요")
        print("예: DATABASE_URL=postgresql+asyncpg://user:pass@localhost/malphago python scripts/migrate_sqlite.py")
        sys.exit(1)

    migrator = Migrator(
        sqlite_path=args.sqlite_path,
        db_url=args.db_url,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    asyncio.run(migrator.run())


if __name__ == "__main__":
    main()
