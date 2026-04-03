"""크롤링 데이터 → PostgreSQL 저장 파이프라인

KRA 크롤러와 Gumbit 크롤러의 결과를 DB 모델에 매핑하여 저장.
- upsert 패턴: 기존 데이터 있으면 업데이트, 없으면 삽입
- 마스터 데이터(말/기수/조교사) 자동 생성
- 변경 감지 및 entry_change_log 기록
"""

import logging
from datetime import date, datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.track import Track
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry
from app.models.race_timing import RaceTiming
from app.models.entry_change_log import EntryChangeLog
from app.crawlers.kra_crawler import (
    RaceResult, RaceCard, EntryData, TimingData, EntryChange, RaceInfo,
)

logger = logging.getLogger(__name__)

TRACK_CODE_MAP = {"S": "서울", "B": "부산", "J": "제주"}


async def _get_or_create_track(session: AsyncSession, code: str) -> int:
    """트랙 ID 조회 (없으면 생성)"""
    result = await session.execute(select(Track).where(Track.code == code))
    track = result.scalar_one_or_none()
    if track:
        return track.id
    track = Track(code=code, name=TRACK_CODE_MAP.get(code, code), name_en=code)
    session.add(track)
    await session.flush()
    return track.id


async def _get_or_create_horse(session: AsyncSession, name: str, **kwargs) -> int:
    """말 ID 조회/생성"""
    if not name:
        return None
    result = await session.execute(select(Horse).where(Horse.name == name))
    horse = result.scalar_one_or_none()
    if horse:
        # 기존 데이터 업데이트
        for k, v in kwargs.items():
            if v and hasattr(horse, k):
                setattr(horse, k, v)
        return horse.id
    horse = Horse(name=name, **{k: v for k, v in kwargs.items() if v})
    session.add(horse)
    await session.flush()
    return horse.id


async def _get_or_create_jockey(session: AsyncSession, name: str) -> int | None:
    """기수 ID 조회/생성"""
    if not name:
        return None
    result = await session.execute(select(Jockey).where(Jockey.name == name))
    jockey = result.scalar_one_or_none()
    if jockey:
        return jockey.id
    jockey = Jockey(name=name)
    session.add(jockey)
    await session.flush()
    return jockey.id


async def _get_or_create_trainer(session: AsyncSession, name: str) -> int | None:
    """조교사 ID 조회/생성"""
    if not name:
        return None
    result = await session.execute(select(Trainer).where(Trainer.name == name))
    trainer = result.scalar_one_or_none()
    if trainer:
        return trainer.id
    trainer = Trainer(name=name)
    session.add(trainer)
    await session.flush()
    return trainer.id


async def _find_or_create_race(
    session: AsyncSession, track_id: int, info: RaceInfo
) -> Race:
    """Race 레코드 조회/생성"""
    race_date_obj = date(
        int(info.race_date[:4]),
        int(info.race_date[4:6]),
        int(info.race_date[6:8]),
    )
    result = await session.execute(
        select(Race).where(
            and_(
                Race.track_id == track_id,
                Race.race_date == race_date_obj,
                Race.race_number == info.race_number,
            )
        )
    )
    race = result.scalar_one_or_none()
    if race:
        # 업데이트
        if info.race_level:
            race.race_level = info.race_level
        if info.distance:
            race.distance = info.distance
        if info.weather:
            race.weather = info.weather
        if info.moisture:
            race.moisture = info.moisture
        if info.race_time:
            race.race_time = info.race_time
        if info.total_entries:
            race.total_entries = info.total_entries
        if info.prize_1st:
            race.prize_1st = info.prize_1st
        if info.prize_2nd:
            race.prize_2nd = info.prize_2nd
        if info.prize_3rd:
            race.prize_3rd = info.prize_3rd
        return race

    race = Race(
        track_id=track_id,
        race_date=race_date_obj,
        race_number=info.race_number,
        race_name=info.race_name,
        race_level=info.race_level,
        distance=info.distance,
        surface=info.surface,
        weather=info.weather,
        moisture=info.moisture,
        total_entries=info.total_entries,
        prize_1st=info.prize_1st,
        prize_2nd=info.prize_2nd,
        prize_3rd=info.prize_3rd,
        race_time=info.race_time,
    )
    session.add(race)
    await session.flush()
    return race


# ──────────────────────── Race Result 저장 ────────────────────────

async def save_race_result(session: AsyncSession, result: RaceResult) -> Race | None:
    """경주 성적(KRA 성적표) → DB 저장"""
    if not result.info:
        return None

    track_id = await _get_or_create_track(session, result.info.track_code)
    race = await _find_or_create_race(session, track_id, result.info)

    # 기존 entries 조회 (업데이트용)
    existing_entries = {}
    existing_result = await session.execute(
        select(RaceEntry).where(RaceEntry.race_id == race.id)
    )
    for entry in existing_result.scalars():
        existing_entries[entry.horse_number] = entry

    # 엔트리 저장
    entry_map = {}  # horse_number -> RaceEntry
    for ed in result.entries:
        horse_id = await _get_or_create_horse(
            session, ed.horse_name, origin=ed.origin, gender=ed.gender
        )
        jockey_id = await _get_or_create_jockey(session, ed.jockey_name)
        trainer_id = await _get_or_create_trainer(session, ed.trainer_name)

        if ed.horse_number in existing_entries:
            entry = existing_entries[ed.horse_number]
            entry.horse_id = horse_id
            entry.jockey_id = jockey_id
            entry.trainer_id = trainer_id
            entry.ranking = ed.ranking
            entry.rating = ed.rating
            entry.weight = ed.weight
            entry.horse_weight = ed.horse_weight
            entry.horse_weight_change = ed.horse_weight_change
            entry.finish_margin = ed.finish_margin
            entry.odds_win = ed.odds_win
            entry.odds_place = ed.odds_place
            entry.equipment = ed.equipment
        else:
            entry = RaceEntry(
                race_id=race.id,
                horse_id=horse_id,
                jockey_id=jockey_id,
                trainer_id=trainer_id,
                horse_number=ed.horse_number,
                ranking=ed.ranking,
                favor_ranking=None,
                rating=ed.rating,
                weight=ed.weight,
                horse_weight=ed.horse_weight,
                horse_weight_change=ed.horse_weight_change,
                finish_margin=ed.finish_margin,
                odds_win=ed.odds_win,
                odds_place=ed.odds_place,
                equipment=ed.equipment,
            )
            session.add(entry)
            await session.flush()

        entry_map[ed.horse_number] = entry

    # 구간기록 저장
    for td in result.timings:
        entry = entry_map.get(td.horse_number)
        if not entry:
            continue

        # 기존 timing 조회
        timing_result = await session.execute(
            select(RaceTiming).where(RaceTiming.entry_id == entry.id)
        )
        timing = timing_result.scalar_one_or_none()

        if timing:
            timing.corner_1 = td.corner_1
            timing.corner_2 = td.corner_2
            timing.corner_3 = td.corner_3
            timing.corner_4 = td.corner_4
            timing.s1f = td.s1f
            timing.g3f = td.g3f
            timing.g1f = td.g1f
            timing.split_3f_g = td.split_3f_g
            timing.split_1f_g = td.split_1f_g
            timing.record_full = td.record_full
        else:
            timing = RaceTiming(
                entry_id=entry.id,
                corner_1=td.corner_1,
                corner_2=td.corner_2,
                corner_3=td.corner_3,
                corner_4=td.corner_4,
                s1f=td.s1f,
                g3f=td.g3f,
                g1f=td.g1f,
                split_3f_g=td.split_3f_g,
                split_1f_g=td.split_1f_g,
                record_full=td.record_full,
            )
            session.add(timing)

    await session.commit()
    logger.info(f"Saved result: {result.info.track_code} {result.info.race_date} {result.info.race_number}R")
    return race


# ──────────────────────── Race Card 저장 ────────────────────────

async def save_race_card(session: AsyncSession, card: RaceCard) -> Race | None:
    """출마표(KRA 출주표) → DB 저장 + 변경감지"""
    if not card.info:
        return None

    track_id = await _get_or_create_track(session, card.info.track_code)
    race = await _find_or_create_race(session, track_id, card.info)

    # 기존 entries 조회 (변경 감지용)
    existing_entries = {}
    existing_result = await session.execute(
        select(RaceEntry).where(RaceEntry.race_id == race.id)
    )
    for entry in existing_result.scalars():
        existing_entries[entry.horse_number] = entry

    for ed in card.entries:
        horse_id = await _get_or_create_horse(
            session, ed.horse_name, origin=ed.origin, gender=ed.gender
        )
        jockey_id = await _get_or_create_jockey(session, ed.jockey_name)
        trainer_id = await _get_or_create_trainer(session, ed.trainer_name)

        if ed.horse_number in existing_entries:
            entry = existing_entries[ed.horse_number]

            # 기수 변경 감지
            if entry.jockey_id and jockey_id and entry.jockey_id != jockey_id:
                old_jockey = await session.get(Jockey, entry.jockey_id)
                change = EntryChangeLog(
                    race_id=race.id,
                    entry_id=entry.id,
                    change_type="jockey_change",
                    field_name="jockey_name",
                    old_value=old_jockey.name if old_jockey else str(entry.jockey_id),
                    new_value=ed.jockey_name,
                    source="auto",
                )
                session.add(change)
                logger.warning(
                    f"Jockey change detected: {card.info.track_code} "
                    f"{card.info.race_number}R #{ed.horse_number} "
                    f"{old_jockey.name if old_jockey else '?'} → {ed.jockey_name}"
                )

            # 업데이트
            entry.horse_id = horse_id
            entry.jockey_id = jockey_id
            entry.trainer_id = trainer_id
            entry.rating = ed.rating or entry.rating
            entry.weight = ed.weight or entry.weight
        else:
            entry = RaceEntry(
                race_id=race.id,
                horse_id=horse_id,
                jockey_id=jockey_id,
                trainer_id=trainer_id,
                horse_number=ed.horse_number,
                rating=ed.rating,
                weight=ed.weight,
            )
            session.add(entry)

    await session.commit()
    logger.info(f"Saved card: {card.info.track_code} {card.info.race_date} {card.info.race_number}R")
    return race


# ──────────────────────── Entry Changes 저장 ────────────────────────

async def save_entry_changes(
    session: AsyncSession, changes: list[EntryChange]
) -> int:
    """출전변경 데이터 저장"""
    saved = 0
    for change in changes:
        track_id = await _get_or_create_track(session, change.track_code)

        race_date_obj = date(
            int(change.race_date[:4]),
            int(change.race_date[4:6]),
            int(change.race_date[6:8]),
        )
        result = await session.execute(
            select(Race).where(
                and_(
                    Race.track_id == track_id,
                    Race.race_date == race_date_obj,
                    Race.race_number == change.race_number,
                )
            )
        )
        race = result.scalar_one_or_none()
        if not race:
            continue

        log = EntryChangeLog(
            race_id=race.id,
            change_type=change.change_type,
            field_name=change.field_name,
            old_value=change.old_value,
            new_value=change.new_value,
            source="auto",
        )
        session.add(log)
        saved += 1

    await session.commit()
    logger.info(f"Saved {saved} entry changes")
    return saved


# ──────────────────────── Batch 저장 ────────────────────────

async def save_race_day_results(
    session: AsyncSession, results: list[RaceResult]
) -> int:
    """하루 전체 경주 성적 일괄 저장"""
    saved = 0
    for result in results:
        race = await save_race_result(session, result)
        if race:
            saved += 1
    return saved


async def save_race_day_cards(
    session: AsyncSession, cards: list[RaceCard]
) -> int:
    """하루 전체 출마표 일괄 저장"""
    saved = 0
    for card in cards:
        race = await save_race_card(session, card)
        if race:
            saved += 1
    return saved
