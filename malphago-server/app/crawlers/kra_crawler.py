"""KRA(한국마사회) 크롤러 - Playwright async 기반

크롤링 대상:
1. 경주 성적표 (과거 결과): ScoretableDetailList.do
2. 출마표 (당일 출주): TodayRaceList.do (TodayPlayer)

기존 hracing/kra_crawler.py + test.py 기반 이식
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

KRA_BASE = "https://race.kra.co.kr"
MEET_CODES = {"S": "1", "B": "2", "J": "3"}  # 서울/부산/제주


@dataclass
class RaceResult:
    """경주 성적 데이터"""
    race_date: str
    track_code: str
    race_number: int
    race_name: str = ""
    race_level: str = ""
    distance: int = 0
    weather: str = ""
    moisture: str = ""
    race_time: str = ""
    entries: list = field(default_factory=list)
    timings: list = field(default_factory=list)


@dataclass
class EntryData:
    """출주마 데이터"""
    ranking: int | None = None
    horse_number: int | None = None
    horse_name: str = ""
    origin: str = ""
    gender: str = ""
    age: int | None = None
    weight: str = ""
    rating: int | None = None
    jockey_name: str = ""
    trainer_name: str = ""
    owner_name: str = ""
    finish_margin: str = ""
    horse_weight: int | None = None
    horse_weight_change: int | None = None
    odds_win: float | None = None
    odds_place: float | None = None
    equipment: str = ""


@dataclass
class TimingData:
    """구간 기록 데이터"""
    horse_number: int | None = None
    ranking: int | None = None
    corner_pass: str = ""  # 코너통과순위 원문
    corner_1: str = ""
    corner_2: str = ""
    corner_3: str = ""
    corner_4: str = ""
    s1f: float | None = None
    g3f: float | None = None
    g1f: float | None = None
    split_3f_g: float | None = None
    split_1f_g: float | None = None
    record_full: str = ""


def _safe_int(val: str) -> int | None:
    try:
        return int(val.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _safe_float(val: str) -> float | None:
    try:
        return float(val.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _parse_horse_weight(text: str) -> tuple[int | None, int | None]:
    """마체중 텍스트에서 체중과 증감 추출. 예: '452(+2)' -> (452, 2)"""
    match = re.match(r"(\d+)\s*\(([+-]?\d+)\)", text.strip())
    if match:
        return int(match.group(1)), int(match.group(2))
    w = _safe_int(text)
    return w, None


def _parse_corners(corner_text: str) -> tuple[str, str, str, str]:
    """코너통과순위 파싱. 예: '3-2-2-1' -> ('3','2','2','1')"""
    parts = corner_text.strip().split("-")
    while len(parts) < 4:
        parts.append("")
    return parts[0], parts[1], parts[2], parts[3]


async def _navigate_to_race(page: Page, meet: str, rc_date: str, rc_no: str):
    """KRA 성적표 상세 페이지로 이동"""
    await page.goto(
        f"{KRA_BASE}/raceScore/ScoretableScoreList.do?Act=04&Sub=1&meet={meet}",
        timeout=60000,
    )
    await page.evaluate(f"""
        document.getElementById('scoreDaily').meet.value = '{meet}';
        document.getElementById('scoreDaily').realRcDate.value = '{rc_date}';
        document.getElementById('scoreDaily').realRcNo.value = '{rc_no}';
        document.getElementById('scoreDaily').action = '/raceScore/ScoretableDetailList.do';
        document.getElementById('scoreDaily').method = 'post';
        document.getElementById('scoreDaily').submit();
    """)
    await page.wait_for_url("**/ScoretableDetailList.do", timeout=20000)
    await asyncio.sleep(1.5)


async def _parse_race_detail_table(table, caption_text: str) -> list[EntryData]:
    """경주상세성적 테이블 파싱"""
    rows = await table.query_selector_all("tbody tr")
    entries = []
    for row in rows:
        tds = await row.query_selector_all("td")
        if len(tds) < 15:
            continue
        texts = [await td.inner_text() for td in tds]
        hw, hwc = _parse_horse_weight(texts[12])
        entry = EntryData(
            ranking=_safe_int(texts[0]),
            horse_number=_safe_int(texts[1]),
            horse_name=texts[2].strip(),
            origin=texts[3].strip(),
            gender=texts[4].strip(),
            age=_safe_int(texts[5]),
            weight=texts[6].strip(),
            rating=_safe_int(texts[7]),
            jockey_name=texts[8].strip(),
            trainer_name=texts[9].strip(),
            owner_name=texts[10].strip(),
            finish_margin=texts[11].strip(),
            horse_weight=hw,
            horse_weight_change=hwc,
            odds_win=_safe_float(texts[13]),
            odds_place=_safe_float(texts[14]),
            equipment=texts[15].strip() if len(tds) > 15 else "",
        )
        entries.append(entry)
    return entries


async def _parse_timing_table(table, caption_text: str) -> list[TimingData]:
    """구간기록 테이블 파싱 (서울 형식: 코너통과순위 + S1F + 1C~4C + G3F + G1F)"""
    rows = await table.query_selector_all("tbody tr")
    timings = []
    for row in rows:
        tds = await row.query_selector_all("td")
        if len(tds) < 13:
            continue
        texts = [await td.inner_text() for td in tds]
        c1, c2, c3, c4 = _parse_corners(texts[2])
        timing = TimingData(
            ranking=_safe_int(texts[0]),
            horse_number=_safe_int(texts[1]),
            corner_pass=texts[2].strip(),
            corner_1=c1,
            corner_2=c2,
            corner_3=c3,
            corner_4=c4,
            s1f=_safe_float(texts[3]),
            g3f=_safe_float(texts[7]),
            g1f=_safe_float(texts[9]),
            split_3f_g=_safe_float(texts[10]),
            split_1f_g=_safe_float(texts[11]),
            record_full=texts[12].strip(),
        )
        timings.append(timing)
    return timings


async def crawl_race_result(
    track_code: str, rc_date: str, rc_no: int
) -> RaceResult | None:
    """단일 경주 결과 크롤링

    Args:
        track_code: 경마장 코드 (S/B/J)
        rc_date: 경주일 (YYYYMMDD)
        rc_no: 경주 회차 (1~)

    Returns:
        RaceResult or None
    """
    meet = MEET_CODES.get(track_code.upper(), "1")
    result = RaceResult(
        race_date=rc_date,
        track_code=track_code.upper(),
        race_number=rc_no,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await _navigate_to_race(page, meet, rc_date, str(rc_no))

            tables = await page.query_selector_all("div.tableType2 > table")
            if not tables:
                logger.warning(f"No tables found for {track_code} {rc_date} {rc_no}R")
                return None

            for table in tables:
                caption_el = await table.query_selector("caption")
                caption = await caption_el.inner_text() if caption_el else ""

                if "경주상세성적" in caption:
                    result.entries = await _parse_race_detail_table(table, caption)
                elif "코너별통과순위" in caption:
                    result.timings = await _parse_timing_table(table, caption)

            logger.info(
                f"Crawled {track_code} {rc_date} {rc_no}R: "
                f"{len(result.entries)} entries, {len(result.timings)} timings"
            )
            return result
        finally:
            await browser.close()


async def crawl_race_day(track_code: str, rc_date: str, max_races: int = 12) -> list[RaceResult]:
    """하루 전체 경주 결과 크롤링"""
    results = []
    meet = MEET_CODES.get(track_code.upper(), "1")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            for rc_no in range(1, max_races + 1):
                try:
                    await _navigate_to_race(page, meet, rc_date, str(rc_no))
                    tables = await page.query_selector_all("div.tableType2 > table")
                    if not tables:
                        logger.info(f"No more races after {rc_no - 1}R")
                        break

                    result = RaceResult(
                        race_date=rc_date,
                        track_code=track_code.upper(),
                        race_number=rc_no,
                    )

                    for table in tables:
                        caption_el = await table.query_selector("caption")
                        caption = await caption_el.inner_text() if caption_el else ""
                        if "경주상세성적" in caption:
                            result.entries = await _parse_race_detail_table(table, caption)
                        elif "코너별통과순위" in caption:
                            result.timings = await _parse_timing_table(table, caption)

                    if result.entries:
                        results.append(result)
                        logger.info(f"  {rc_no}R: {len(result.entries)} entries")

                except Exception as e:
                    logger.error(f"Error crawling {track_code} {rc_date} {rc_no}R: {e}")
                    continue
        finally:
            await browser.close()

    logger.info(f"Total: {track_code} {rc_date} - {len(results)} races crawled")
    return results
