"""KRA 공공데이터 API 클라이언트 (data.go.kr)

Playwright 웹 크롤링 대신 data.go.kr REST API를 사용하여
경주결과, 출마표, 경주마/기수/조교사 정보를 수집한다.

무료 10,000 요청/일. ServiceKey 필요.
트랙 코드: 1=서울, 2=제주, 3=부산
"""

import asyncio
import logging
from datetime import date
from urllib.parse import quote_plus

import httpx

from app.core.config import settings
from app.crawlers.kra_crawler import (
    RaceInfo,
    EntryData,
    TimingData,
    RaceResult,
    RaceCard,
    HorseProfile,
    JockeyInfo,
    TrainerInfo,
    _safe_int,
    _safe_float,
    _parse_corners,
)

logger = logging.getLogger(__name__)

# API 엔드포인트
API_BASE = "https://apis.data.go.kr/B551015"
ENDPOINTS = {
    "race_result_detail": f"{API_BASE}/racedetailresult/getracedetailresult",
    "race_result_ai": f"{API_BASE}/API155/raceResult",
    "race_info_seoul": f"{API_BASE}/API311/textDataHoldSeRaceInfo",
    "entry_registration": f"{API_BASE}/API323/textDataHoldSeRegInfo",
    "horse_weight": f"{API_BASE}/API317/textDataHoldSeWegInfo",
    "horse_info": f"{API_BASE}/API310/raceHorseInfo",
    "horse_info_old": f"{API_BASE}/API8_2/raceHorseInfo_2",
    "jockey_result": f"{API_BASE}/API11_1/jockeyResult_1",
    "trainer_info": f"{API_BASE}/API308/trainerInfo",
    "rc_race_info": f"{API_BASE}/API186_1/SeoulRace_1",
}

# 앱 내부 트랙코드 → API meet 코드
MEET_CODES = {"S": "1", "B": "3", "J": "2"}


def _get_service_key() -> str:
    key = settings.DATA_GO_KR_SERVICE_KEY
    if not key:
        raise ValueError(
            "DATA_GO_KR_SERVICE_KEY 미설정. "
            "data.go.kr에서 ServiceKey를 발급받아 .env에 설정하세요."
        )
    return key


async def _api_get(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    key: str = "items",
) -> list[dict]:
    """공공데이터 API GET 호출 → items 리스트 반환"""
    params["ServiceKey"] = _get_service_key()
    params.setdefault("_type", "json")
    params.setdefault("numOfRows", "100")
    params.setdefault("pageNo", "1")

    try:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"API HTTP error {e.response.status_code}: {url}")
        return []
    except Exception as e:
        logger.error(f"API error: {url} — {e}")
        return []

    # 공공데이터 응답 구조: response > body > items > item
    body = data.get("response", {}).get("body", {})
    items = body.get("items", {})
    if not items:
        return []
    item_list = items.get("item", [])
    # 단일 항목인 경우 리스트로 변환
    if isinstance(item_list, dict):
        item_list = [item_list]
    return item_list


# ──────────────────────── Race Results (경주결과) ────────────────────────

async def fetch_race_result(
    client: httpx.AsyncClient,
    track_code: str,
    rc_date: str,
    rc_no: int,
) -> RaceResult | None:
    """단일 경주 상세 결과 조회 (API)

    Args:
        client: httpx AsyncClient
        track_code: S/B/J
        rc_date: YYYYMMDD
        rc_no: 경주 회차
    """
    meet = MEET_CODES.get(track_code.upper(), "1")
    items = await _api_get(client, ENDPOINTS["race_result_detail"], {
        "meet": meet,
        "rc_date": rc_date,
        "rc_no": str(rc_no),
    })

    if not items:
        return None

    # 경주 정보 (첫 항목에서 추출)
    first = items[0]
    info = RaceInfo(
        race_date=rc_date,
        track_code=track_code.upper(),
        race_number=rc_no,
        distance=_safe_int(str(first.get("rcDist", ""))) or 0,
        weather=str(first.get("weather", "")).strip(),
    )
    info.total_entries = len(items)

    entries = []
    timings = []

    for item in items:
        horse_weight_raw = str(item.get("wgHr", "")).strip()
        weight_change_raw = str(item.get("df", "")).strip()

        entry = EntryData(
            ranking=_safe_int(str(item.get("stOrd", ""))),
            horse_number=_safe_int(str(item.get("chulNo", ""))),
            horse_name=str(item.get("hrName", "")).strip(),
            horse_id=str(item.get("hrNo", "")).strip(),
            origin=str(item.get("prdCtyNm", "")).strip(),
            gender=str(item.get("sex", "")).strip(),
            age=_safe_int(str(item.get("age", ""))),
            weight=str(item.get("wgBudam", "")).strip(),
            rating=_safe_int(str(item.get("hrRating", ""))),
            jockey_name=str(item.get("jkName", "")).strip(),
            jockey_id=str(item.get("jkNo", "")).strip(),
            trainer_name=str(item.get("trName", "")).strip(),
            trainer_id=str(item.get("trNo", "")).strip(),
            owner_name=str(item.get("owName", "")).strip(),
            finish_margin=str(item.get("differ", "")).strip(),
            horse_weight=_safe_int(horse_weight_raw),
            horse_weight_change=_safe_int(weight_change_raw),
            odds_win=_safe_float(str(item.get("win", ""))),
            odds_place=_safe_float(str(item.get("plc", ""))),
            equipment=str(item.get("hrTool", "")).strip(),
        )
        entries.append(entry)

        # 기록 데이터 (API에서 rcTime으로 제공)
        rc_time = str(item.get("rcTime", "")).strip()
        if rc_time:
            timing = TimingData(
                horse_number=entry.horse_number,
                ranking=entry.ranking,
                record_full=rc_time,
            )
            timings.append(timing)

    result = RaceResult(info=info, entries=entries, timings=timings)
    logger.info(
        f"API Result: {track_code} {rc_date} {rc_no}R — "
        f"{len(entries)} entries"
    )
    return result


async def fetch_race_day_results(
    track_code: str,
    rc_date: str,
    max_races: int = 12,
) -> list[RaceResult]:
    """하루 전체 경주 결과 API 조회"""
    results = []
    async with httpx.AsyncClient() as client:
        for rc_no in range(1, max_races + 1):
            result = await fetch_race_result(client, track_code, rc_date, rc_no)
            if result:
                results.append(result)
            else:
                if rc_no > 3:
                    break
            # API 속도제한 방지
            await asyncio.sleep(0.3)

    logger.info(f"API Day results: {track_code} {rc_date} — {len(results)} races")
    return results


# ──────────────────────── Race Info (경주정보) ────────────────────────

async def fetch_race_info(
    client: httpx.AsyncClient,
    rc_date: str,
) -> list[dict]:
    """특정 날짜 경주 정보 조회 (서울)

    등급, 거리, 출주두수, 상금, 발주시각, 날씨, 주로상태 등
    """
    items = await _api_get(client, ENDPOINTS["race_info_seoul"], {
        "race_dt": rc_date,
        "numOfRows": "20",
    })

    races = []
    for item in items:
        races.append({
            "race_number": _safe_int(str(item.get("raceNo", ""))) or 0,
            "race_name": str(item.get("raceNm", "")).strip(),
            "race_level": str(item.get("gradeNm", "")).strip(),
            "distance": _safe_int(str(item.get("rcDist", ""))) or 0,
            "total_entries": _safe_int(str(item.get("chulTot", ""))) or 0,
            "weather": str(item.get("weather", "")).strip(),
            "moisture": str(item.get("trkCndNm", "")).strip(),
            "race_time": str(item.get("rcTime", "")).strip(),
            "prize_1st": _safe_int(str(item.get("prz1", "")).replace(",", "")) or 0,
            "prize_2nd": _safe_int(str(item.get("prz2", "")).replace(",", "")) or 0,
            "prize_3rd": _safe_int(str(item.get("prz3", "")).replace(",", "")) or 0,
            "prize_4th": _safe_int(str(item.get("prz4", "")).replace(",", "")) or 0,
            "prize_5th": _safe_int(str(item.get("prz5", "")).replace(",", "")) or 0,
        })

    logger.info(f"API Race info: {rc_date} — {len(races)} races")
    return races


# ──────────────────────── Race Card (출마표/출마등록) ────────────────────────

async def fetch_race_card(
    client: httpx.AsyncClient,
    rc_date: str,
    rc_no: int,
) -> RaceCard | None:
    """단일 경주 출마등록 조회 (서울)"""
    items = await _api_get(client, ENDPOINTS["entry_registration"], {
        "race_dt": rc_date,
        "race_no": str(rc_no),
    })

    if not items:
        return None

    info = RaceInfo(
        race_date=rc_date,
        track_code="S",  # 서울 전용 API
        race_number=rc_no,
    )

    entries = []
    for item in items:
        entry = EntryData(
            horse_number=_safe_int(str(item.get("rcptNo", ""))),
            horse_name=str(item.get("hrnm", "")).strip(),
            origin=str(item.get("prds", "")).strip(),
            gender=str(item.get("gndr", "")).strip(),
            age=_safe_int(str(item.get("ag", ""))),
            trainer_name=str(item.get("trarNm", "")).strip(),
            owner_name=str(item.get("ownerNm", "")).strip(),
            rating=_safe_int(str(item.get("ratg", ""))),
        )
        entries.append(entry)

    info.total_entries = len(entries)
    card = RaceCard(info=info, entries=entries)
    logger.info(f"API Card: S {rc_date} {rc_no}R — {len(entries)} entries")
    return card


async def fetch_race_day_cards(
    rc_date: str,
    max_races: int = 12,
) -> list[RaceCard]:
    """하루 전체 출마표 API 조회 (서울)"""
    cards = []
    async with httpx.AsyncClient() as client:
        for rc_no in range(1, max_races + 1):
            card = await fetch_race_card(client, rc_date, rc_no)
            if card:
                cards.append(card)
            else:
                if rc_no > 3:
                    break
            await asyncio.sleep(0.3)

    logger.info(f"API Day cards: S {rc_date} — {len(cards)} races")
    return cards


# ──────────────────────── Horse Weight (마체중) ────────────────────────

async def fetch_horse_weights(
    client: httpx.AsyncClient,
    rc_date: str,
    rc_no: int,
) -> dict[int, tuple[int | None, int | None]]:
    """경주별 마체중 조회 → {마번: (체중, 증감)}"""
    items = await _api_get(client, ENDPOINTS["horse_weight"], {
        "race_dt": rc_date,
        "race_no": str(rc_no),
    })

    weights = {}
    for item in items:
        horse_num = _safe_int(str(item.get("pthrNo", "")))
        weight = _safe_int(str(item.get("hrWeg", "")))
        change = _safe_int(str(item.get("indec", "")))
        if horse_num:
            weights[horse_num] = (weight, change)

    return weights


# ──────────────────────── Horse Info (경주마 정보) ────────────────────────

async def fetch_horse_info(
    client: httpx.AsyncClient,
    meet: str = "1",
    hr_no: str = "",
    hr_name: str = "",
) -> HorseProfile | None:
    """경주마 프로필 조회 (영문명 포함)"""
    params = {"meet": meet}
    if hr_no:
        params["hr_no"] = hr_no
    if hr_name:
        params["hr_name"] = hr_name

    items = await _api_get(client, ENDPOINTS["horse_info"], params)
    if not items:
        return None

    item = items[0]
    profile = HorseProfile(
        horse_id=str(item.get("hrNo", "")).strip(),
        name=str(item.get("hrName", "")).strip(),
        origin=str(item.get("prdCtyNm", "")).strip(),
        gender=str(item.get("sex", "")).strip(),
        birth_year=str(item.get("birthday", "")).strip()[:4],
        owner=str(item.get("owName", "")).strip(),
        trainer=str(item.get("trName", "")).strip(),
        rating=_safe_int(str(item.get("rating", ""))),
        total_record=(
            f"{item.get('rcCntT', 0)}-{item.get('ord1CntT', 0)}-"
            f"{item.get('ord2CntT', 0)}-{item.get('ord3CntT', 0)}"
        ),
        total_prize=str(item.get("chaksunT", "")).strip(),
        sire=str(item.get("faHrName", "")).strip(),
        dam=str(item.get("moHrName", "")).strip(),
    )

    logger.info(f"API Horse: {profile.name} ({profile.horse_id})")
    return profile


# ──────────────────────── Jockey Info (기수 정보) ────────────────────────

async def fetch_jockey_info(
    client: httpx.AsyncClient,
    meet: str = "1",
    jk_no: str = "",
    jk_name: str = "",
) -> JockeyInfo | None:
    """기수 성적 조회"""
    params = {"meet": meet}
    if jk_no:
        params["jk_no"] = jk_no
    if jk_name:
        params["jk_name"] = jk_name

    items = await _api_get(client, ENDPOINTS["jockey_result"], params)
    if not items:
        return None

    item = items[0]
    return JockeyInfo(
        jockey_id=str(item.get("jkNo", "")).strip(),
        name=str(item.get("jkName", "")).strip(),
        total_starts=_safe_int(str(item.get("rcCntT", ""))) or 0,
        total_wins=_safe_int(str(item.get("ord1CntT", ""))) or 0,
        total_seconds=_safe_int(str(item.get("ord2CntT", ""))) or 0,
        year_starts=_safe_int(str(item.get("rcCntY", ""))) or 0,
        year_wins=_safe_int(str(item.get("ord1CntY", ""))) or 0,
        year_seconds=_safe_int(str(item.get("ord2CntY", ""))) or 0,
    )


async def fetch_all_jockeys(meet: str = "1") -> list[JockeyInfo]:
    """전체 기수 목록 조회"""
    async with httpx.AsyncClient() as client:
        items = await _api_get(client, ENDPOINTS["jockey_result"], {
            "meet": meet,
            "numOfRows": "500",
        })

    jockeys = []
    for item in items:
        jockeys.append(JockeyInfo(
            jockey_id=str(item.get("jkNo", "")).strip(),
            name=str(item.get("jkName", "")).strip(),
            total_starts=_safe_int(str(item.get("rcCntT", ""))) or 0,
            total_wins=_safe_int(str(item.get("ord1CntT", ""))) or 0,
            total_seconds=_safe_int(str(item.get("ord2CntT", ""))) or 0,
            year_starts=_safe_int(str(item.get("rcCntY", ""))) or 0,
            year_wins=_safe_int(str(item.get("ord1CntY", ""))) or 0,
            year_seconds=_safe_int(str(item.get("ord2CntY", ""))) or 0,
        ))

    logger.info(f"API Jockeys: meet={meet} — {len(jockeys)}")
    return jockeys


# ──────────────────────── Trainer Info (조교사 정보) ────────────────────────

async def fetch_trainer_info(
    client: httpx.AsyncClient,
    meet: str = "1",
    tr_no: str = "",
    tr_name: str = "",
) -> TrainerInfo | None:
    """조교사 정보 조회 (영문명 포함)"""
    params = {"meet": meet}
    if tr_no:
        params["tr_no"] = tr_no
    if tr_name:
        params["tr_name"] = tr_name

    items = await _api_get(client, ENDPOINTS["trainer_info"], params)
    if not items:
        return None

    item = items[0]
    return TrainerInfo(
        trainer_id=str(item.get("trNo", "")).strip(),
        name=str(item.get("trName", "")).strip(),
        total_starts=_safe_int(str(item.get("rcCntT", ""))) or 0,
        total_wins=_safe_int(str(item.get("ord1CntT", ""))) or 0,
        year_starts=_safe_int(str(item.get("rcCntY", ""))) or 0,
        year_wins=_safe_int(str(item.get("ord1CntY", ""))) or 0,
    )


async def fetch_all_trainers(meet: str = "1") -> list[TrainerInfo]:
    """전체 조교사 목록 조회"""
    async with httpx.AsyncClient() as client:
        items = await _api_get(client, ENDPOINTS["trainer_info"], {
            "meet": meet,
            "numOfRows": "500",
        })

    trainers = []
    for item in items:
        trainers.append(TrainerInfo(
            trainer_id=str(item.get("trNo", "")).strip(),
            name=str(item.get("trName", "")).strip(),
            total_starts=_safe_int(str(item.get("rcCntT", ""))) or 0,
            total_wins=_safe_int(str(item.get("ord1CntT", ""))) or 0,
            year_starts=_safe_int(str(item.get("rcCntY", ""))) or 0,
            year_wins=_safe_int(str(item.get("ord1CntY", ""))) or 0,
        ))

    logger.info(f"API Trainers: meet={meet} — {len(trainers)}")
    return trainers


# ──────────────────────── AI Race Result (영문 포함) ────────────────────────

async def fetch_race_result_with_english(
    client: httpx.AsyncClient,
    track_code: str,
    rc_date: str,
) -> list[dict]:
    """AI용 경주결과 (영문명 포함) — 전체 경주일 한번에"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    items = await _api_get(client, ENDPOINTS["race_result_ai"], {
        "rccrs_cd": meet,
        "race_dt": rc_date,
        "numOfRows": "200",
    })

    results = []
    for item in items:
        results.append({
            "race_no": _safe_int(str(item.get("raceNo", ""))) or 0,
            "horse_name": str(item.get("hrnm", "")).strip(),
            "horse_name_en": str(item.get("engHrnm", "")).strip(),
            "jockey_name": str(item.get("jckyNm", "")).strip(),
            "jockey_name_en": str(item.get("engJckyNm", "")).strip(),
            "trainer_name": str(item.get("trarNm", "")).strip(),
            "trainer_name_en": str(item.get("engTrarNm", "")).strip(),
            "owner_name": str(item.get("ownerNm", "")).strip(),
            "ranking": _safe_int(str(item.get("rk", ""))),
            "race_time": str(item.get("raceRcd", "")).strip(),
            "margin": str(item.get("margin", "")).strip(),
            "distance": _safe_int(str(item.get("raceDs", ""))) or 0,
            "gate_no": _safe_int(str(item.get("gtno", ""))),
            "rating": _safe_int(str(item.get("ratgSo", ""))),
        })

    return results
