"""data.go.kr KRA 공공데이터 API 클라이언트

경주결과, 마체중, 배당률 등을 수집하여 DB에 저장한다.
Playwright 크롤링 대체용.

사용 전 .env에 DATA_GO_KR_SERVICE_KEY 설정 필요.
"""

import asyncio
import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.horse import Horse
from app.models.jockey import Jockey
from app.models.trainer import Trainer
from app.models.race import Race
from app.models.race_entry import RaceEntry

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.data.go.kr/B551015"

# 트랙 매핑: data.go.kr meet code → DB track_id
MEET_TO_TRACK = {"1": 1, "2": 3, "3": 2}  # 1=서울→1, 2=제주→3, 3=부산→2
TRACK_TO_MEET = {1: "1", 2: "3", 3: "2"}  # DB track_id → meet code


async def _fetch_api(endpoint: str, params: dict) -> list[dict]:
    """data.go.kr API 호출 (XML→JSON 자동 변환)"""
    if not settings.DATA_GO_KR_SERVICE_KEY:
        raise ValueError("DATA_GO_KR_SERVICE_KEY not configured in .env")

    url = f"{BASE_URL}/{endpoint}"
    params = {
        **params,
        "ServiceKey": settings.DATA_GO_KR_SERVICE_KEY,
        "_type": "json",
        "numOfRows": "100",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # data.go.kr 응답 구조: response > body > items > item
    try:
        body = data["response"]["body"]
        total = body.get("totalCount", 0)
        if total == 0:
            return []
        items = body["items"]["item"]
        if isinstance(items, dict):
            items = [items]
        return items
    except (KeyError, TypeError):
        logger.warning(f"Unexpected API response: {data}")
        return []


async def fetch_race_results(
    session: AsyncSession,
    race_date: date,
    meet: str = "1",
) -> dict:
    """경주결과 상세 API로 해당 날짜의 모든 경주 결과를 수집한다.

    API: racedetailresult/getracedetailresult
    Returns: stats dict
    """
    date_str = race_date.strftime("%Y%m%d")
    stats = {"races": 0, "entries_created": 0, "entries_updated": 0, "errors": 0}
    track_id = MEET_TO_TRACK.get(meet, 1)

    for rc_no in range(1, 13):  # 최대 12경주
        try:
            items = await _fetch_api(
                "racedetailresult/getracedetailresult",
                {"meet": meet, "rc_date": date_str, "rc_no": str(rc_no)},
            )
            if not items:
                continue

            stats["races"] += 1

            # Race 생성/조회
            race = await _get_or_create_race(
                session, track_id, race_date, rc_no, items[0]
            )

            for item in items:
                try:
                    await _upsert_entry_from_result(session, race, item)
                    stats["entries_updated"] += 1
                except Exception as e:
                    logger.warning(f"Entry error R{rc_no}: {e}")
                    stats["errors"] += 1

            await session.flush()

        except Exception as e:
            logger.warning(f"Race {rc_no} fetch error: {e}")
            stats["errors"] += 1

        # Rate limiting
        await asyncio.sleep(0.2)

    logger.info(f"Race results for {race_date} (meet={meet}): {stats}")
    return stats


async def _get_or_create_race(
    session: AsyncSession,
    track_id: int,
    race_date: date,
    race_number: int,
    item: dict,
) -> Race:
    """경주 조회 또는 생성"""
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
        )
        session.add(race)
        await session.flush()

    # API 데이터로 보강
    race_name = item.get("rcName") or item.get("rc_name")
    if race_name and not race.race_name:
        race.race_name = str(race_name).strip()

    distance = _parse_int(item.get("rcDist") or item.get("rc_dist"))
    if distance and not race.distance:
        race.distance = distance

    surface = item.get("track") or item.get("track_nm")
    if surface:
        race.surface = str(surface).strip()

    weather = item.get("weather")
    if weather:
        race.weather = str(weather).strip()

    moisture = item.get("mois") or item.get("moisture")
    if moisture:
        race.moisture = str(moisture).strip()

    total_entries = _parse_int(item.get("rcHorseNum") or item.get("horse_cnt"))
    if total_entries:
        race.total_entries = total_entries

    race_time = item.get("rcTime") or item.get("rc_time")
    if race_time:
        race.race_time = str(race_time).strip()

    return race


async def _upsert_entry_from_result(
    session: AsyncSession,
    race: Race,
    item: dict,
) -> RaceEntry:
    """경주결과 API 항목에서 RaceEntry를 생성 또는 업데이트한다."""
    horse_name = str(item.get("hrName") or item.get("hr_name", "")).strip()
    jockey_name = str(item.get("jkName") or item.get("jk_name", "")).strip()
    trainer_name = str(item.get("trName") or item.get("tr_name", "")).strip()

    if not horse_name:
        return

    # 마스터 조회/생성
    horse_id = await _get_or_create_entity(session, Horse, horse_name)
    jockey_id = await _get_or_create_entity(session, Jockey, jockey_name) if jockey_name else None
    trainer_id = await _get_or_create_entity(session, Trainer, trainer_name) if trainer_name else None

    # Entry 조회 또는 생성
    q = select(RaceEntry).where(
        RaceEntry.race_id == race.id,
        RaceEntry.horse_id == horse_id,
    )
    result = await session.execute(q)
    entry = result.scalar_one_or_none()

    if not entry:
        entry = RaceEntry(race_id=race.id, horse_id=horse_id)
        session.add(entry)

    # 기본 정보
    entry.jockey_id = jockey_id or entry.jockey_id
    entry.trainer_id = trainer_id or entry.trainer_id
    entry.horse_number = _parse_int(item.get("hrNo") or item.get("hr_no")) or entry.horse_number
    entry.ranking = _parse_int(item.get("ord") or item.get("rank")) or entry.ranking
    entry.favor_ranking = _parse_int(item.get("favOrd") or item.get("fav_ord")) or entry.favor_ranking

    # 마체중 (핵심 누락 데이터)
    weight = _parse_int(item.get("hrWeight") or item.get("hr_weight"))
    if weight:
        entry.horse_weight = weight
    weight_change = _parse_int(item.get("hrWeightInc") or item.get("hr_weight_inc"))
    if weight_change is not None:
        entry.horse_weight_change = weight_change

    # 배당률
    odds_win = _parse_float(item.get("winOdds") or item.get("win_odds"))
    if odds_win:
        entry.odds_win = odds_win
    odds_place = _parse_float(item.get("plcOdds") or item.get("plc_odds"))
    if odds_place:
        entry.odds_place = odds_place

    # 레이팅
    rating = _parse_int(item.get("rating") or item.get("raRating"))
    if rating:
        entry.rating = rating

    # 부담중량
    weight_carry = item.get("wgHr") or item.get("wg_hr")
    if weight_carry:
        entry.weight = str(weight_carry).strip()

    return entry


async def _get_or_create_entity(session: AsyncSession, model_class, name: str) -> int:
    """Horse/Jockey/Trainer 조회 또는 생성하여 ID 반환"""
    result = await session.execute(
        select(model_class).where(model_class.name == name)
    )
    entity = result.scalar_one_or_none()
    if not entity:
        entity = model_class(name=name)
        session.add(entity)
        await session.flush()
    return entity.id


def _parse_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _parse_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


async def collect_date_range(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    meets: list[str] | None = None,
) -> dict:
    """날짜 범위의 경주 결과를 수집한다.

    Args:
        session: DB session
        start_date: 시작 날짜
        end_date: 종료 날짜
        meets: 경마장 코드 목록 (기본: 서울+부산)
    """
    if meets is None:
        meets = ["1", "3"]  # 서울, 부산

    total_stats = {"dates": 0, "races": 0, "entries": 0, "errors": 0}
    current = start_date

    while current <= end_date:
        # 경마는 주로 금/토/일 개최
        if current.weekday() in (4, 5, 6):  # Fri, Sat, Sun
            for meet in meets:
                try:
                    stats = await fetch_race_results(session, current, meet)
                    total_stats["races"] += stats["races"]
                    total_stats["entries"] += stats["entries_updated"]
                    total_stats["errors"] += stats["errors"]
                except Exception as e:
                    logger.error(f"Collection error {current} meet={meet}: {e}")
                    total_stats["errors"] += 1

                await asyncio.sleep(0.5)  # Rate limiting between meets

            if total_stats["races"] > 0:
                total_stats["dates"] += 1
                await session.commit()

        current += timedelta(days=1)

    logger.info(f"Collection complete: {total_stats}")
    return total_stats
