"""KRA(한국마사회) 크롤러 - Playwright async 기반

사이트 분석(2026-04-03) 기반 신규 작성.

크롤링 대상 페이지:
1. 출마표 상세 (chulmaDetailInfoChulmapyo.do) — 당일 출주표
2. 경주 성적표 (ScoretableDetailList.do) — 과거 경주 결과 + 구간기록
3. 출전변경 (ChulmapyoChange.do) — 기수/말 변경 감지
4. 경주마 프로필 (profileHorseItem.do) — 말 상세정보
5. 기수 목록 (ProfileJockeyListActive.do) — 기수 정보
6. 조교사 목록 (profileTrainerList.do) — 조교사 정보

URL 파라미터:
- meet: 1=서울, 2=제주, 3=부산
- rcDate/realRcDate: YYYYMMDD
- rcNo/realRcNo: 경주 회차
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

KRA_BASE = "https://race.kra.co.kr"
MEET_CODES = {"S": "1", "B": "3", "J": "2"}  # 서울=1, 제주=2, 부산=3


# ──────────────────────── Dataclasses ────────────────────────

@dataclass
class RaceInfo:
    """경주 기본 정보 (출마표/성적표 공통)"""
    race_date: str  # YYYYMMDD
    track_code: str  # S/B/J
    race_number: int
    race_name: str = ""
    race_level: str = ""       # 등급
    distance: int = 0          # 거리(m)
    surface: str = ""          # 주로 (잔디/모래)
    weather: str = ""          # 날씨
    moisture: str = ""         # 함수율
    total_entries: int = 0     # 출주두수
    race_time: str = ""        # 발주시각 or 경주기록
    prize_1st: int = 0
    prize_2nd: int = 0
    prize_3rd: int = 0
    prize_4th: int = 0
    prize_5th: int = 0


@dataclass
class EntryData:
    """출주마 데이터 (출마표 + 성적표 통합)"""
    horse_number: int | None = None       # 마번
    horse_name: str = ""                  # 마명
    horse_id: str = ""                    # hrNo (KRA 내부 ID)
    origin: str = ""                      # 산지
    gender: str = ""                      # 성별
    age: int | None = None                # 마령
    color: str = ""                       # 모색
    weight: str = ""                      # 부담중량
    rating: int | None = None             # 레이팅
    jockey_name: str = ""                 # 기수명
    jockey_id: str = ""                   # jkNo
    trainer_name: str = ""                # 조교사명
    trainer_id: str = ""                  # trNo
    owner_name: str = ""                  # 마주명
    recent_record: str = ""               # 최근전적
    # 결과 데이터 (성적표에서만)
    ranking: int | None = None            # 순위
    finish_margin: str = ""               # 도착차
    horse_weight: int | None = None       # 마체중
    horse_weight_change: int | None = None  # 마체중증감
    odds_win: float | None = None         # 단승배당
    odds_place: float | None = None       # 연승배당
    equipment: str = ""                   # 장구현황
    race_interval: int | None = None      # 출전간격(일)


@dataclass
class TimingData:
    """구간 기록 데이터"""
    horse_number: int | None = None
    ranking: int | None = None
    corner_pass: str = ""     # 코너통과순위 원문 (예: 3-2-2-1)
    corner_1: str = ""
    corner_2: str = ""
    corner_3: str = ""
    corner_4: str = ""
    s1f: float | None = None       # S1F (초반 1할롱)
    g3f: float | None = None       # G3F (끝 3할롱)
    g1f: float | None = None       # G1F (끝 1할롱)
    split_3f_g: float | None = None
    split_1f_g: float | None = None
    record_full: str = ""          # 전체 기록


@dataclass
class RaceResult:
    """경주 결과 (성적표)"""
    info: RaceInfo | None = None
    entries: list[EntryData] = field(default_factory=list)
    timings: list[TimingData] = field(default_factory=list)


@dataclass
class RaceCard:
    """출마표 (당일 출주)"""
    info: RaceInfo | None = None
    entries: list[EntryData] = field(default_factory=list)


@dataclass
class EntryChange:
    """출전변경 데이터"""
    race_date: str = ""
    track_code: str = ""
    race_number: int = 0
    horse_name: str = ""
    change_type: str = ""    # jockey_change / horse_scratch / weight_change
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""


@dataclass
class HorseProfile:
    """경주마 프로필"""
    horse_id: str = ""       # hrNo
    name: str = ""
    origin: str = ""         # 산지
    gender: str = ""
    birth_year: str = ""
    color: str = ""
    sire: str = ""           # 부마
    dam: str = ""            # 모마
    owner: str = ""
    trainer: str = ""
    grade: str = ""          # 등급
    rating: int | None = None
    total_record: str = ""   # 통산 전적
    total_prize: str = ""    # 통산 상금
    debut_date: str = ""


@dataclass
class JockeyInfo:
    """기수 정보"""
    jockey_id: str = ""      # jkNo
    name: str = ""
    affiliation: str = ""    # 소속조
    debut_date: str = ""     # 면허일자
    weight: str = ""         # 체중
    total_starts: int = 0
    total_wins: int = 0
    total_seconds: int = 0
    total_thirds: int = 0
    year_starts: int = 0     # 금년 전적
    year_wins: int = 0
    year_seconds: int = 0
    year_thirds: int = 0


@dataclass
class TrainerInfo:
    """조교사 정보"""
    trainer_id: str = ""     # trNo
    name: str = ""
    affiliation: str = ""
    total_starts: int = 0
    total_wins: int = 0
    year_starts: int = 0
    year_wins: int = 0


# ──────────────────────── Utility ────────────────────────

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


def _parse_prize_text(text: str) -> int:
    """상금 텍스트 파싱. 예: '30,000' -> 30000"""
    return _safe_int(text) or 0


# ──────────────────────── Race Result (성적표) ────────────────────────

async def _goto_race_result_page(page: Page, meet: str, rc_date: str, rc_no: str):
    """KRA 경주 성적표 상세 페이지로 이동 (직접 URL 접근)"""
    url = (
        f"{KRA_BASE}/raceScore/ScoretableDetailList.do"
        f"?Act=04&Sub=2&meet={meet}&realRcDate={rc_date}&realRcNo={rc_no}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)


async def _parse_race_header(page: Page) -> RaceInfo:
    """성적표 헤더에서 경주 정보 추출"""
    info = RaceInfo(race_date="", track_code="", race_number=0)

    # 제목/등급/거리 등 헤더 정보 파싱
    header = await page.query_selector("div.race_info, div.raceInfoWrap, h3.race_title")
    if header:
        text = await header.inner_text()
        # 거리 추출
        dist_match = re.search(r"(\d{3,4})[mM]", text)
        if dist_match:
            info.distance = int(dist_match.group(1))
        # 등급 추출
        level_match = re.search(r"(\d+)급", text)
        if level_match:
            info.race_level = level_match.group(1)

    # 날씨/주로상태 테이블에서 추출
    info_cells = await page.query_selector_all("th, td")
    for i, cell in enumerate(info_cells):
        text = (await cell.inner_text()).strip()
        if "날씨" in text and i + 1 < len(info_cells):
            info.weather = (await info_cells[i + 1].inner_text()).strip()
        elif "주로" in text and "상태" in text and i + 1 < len(info_cells):
            info.moisture = (await info_cells[i + 1].inner_text()).strip()

    return info


async def _parse_result_entries(page: Page) -> list[EntryData]:
    """경주상세성적 테이블 파싱"""
    entries = []
    tables = await page.query_selector_all("table")

    for table in tables:
        caption_el = await table.query_selector("caption")
        caption = await caption_el.inner_text() if caption_el else ""
        if "경주상세성적" not in caption and "성적" not in caption:
            continue

        rows = await table.query_selector_all("tbody tr")
        for row in rows:
            tds = await row.query_selector_all("td")
            if len(tds) < 15:
                continue
            texts = [await td.inner_text() for td in tds]
            hw, hwc = _parse_horse_weight(texts[12] if len(texts) > 12 else "")

            # hrNo 추출 (링크에서)
            horse_link = await row.query_selector("a[href*='hrNo'], a[onclick*='hrNo']")
            horse_id = ""
            if horse_link:
                onclick = await horse_link.get_attribute("onclick") or ""
                href = await horse_link.get_attribute("href") or ""
                id_match = re.search(r"hrNo[='\"](\d+)", onclick + href)
                if id_match:
                    horse_id = id_match.group(1)

            entry = EntryData(
                ranking=_safe_int(texts[0]),
                horse_number=_safe_int(texts[1]),
                horse_name=texts[2].strip(),
                horse_id=horse_id,
                origin=texts[3].strip() if len(texts) > 3 else "",
                gender=texts[4].strip() if len(texts) > 4 else "",
                age=_safe_int(texts[5]) if len(texts) > 5 else None,
                weight=texts[6].strip() if len(texts) > 6 else "",
                rating=_safe_int(texts[7]) if len(texts) > 7 else None,
                jockey_name=texts[8].strip() if len(texts) > 8 else "",
                trainer_name=texts[9].strip() if len(texts) > 9 else "",
                owner_name=texts[10].strip() if len(texts) > 10 else "",
                finish_margin=texts[11].strip() if len(texts) > 11 else "",
                horse_weight=hw,
                horse_weight_change=hwc,
                odds_win=_safe_float(texts[13]) if len(texts) > 13 else None,
                odds_place=_safe_float(texts[14]) if len(texts) > 14 else None,
                equipment=texts[15].strip() if len(texts) > 15 else "",
            )
            entries.append(entry)
        break  # 첫 번째 성적 테이블만

    return entries


async def _parse_timing_entries(page: Page) -> list[TimingData]:
    """구간기록/코너별통과순위 테이블 파싱"""
    timings = []
    tables = await page.query_selector_all("table")

    for table in tables:
        caption_el = await table.query_selector("caption")
        caption = await caption_el.inner_text() if caption_el else ""
        if "코너" not in caption and "구간" not in caption:
            continue

        rows = await table.query_selector_all("tbody tr")
        for row in rows:
            tds = await row.query_selector_all("td")
            if len(tds) < 10:
                continue
            texts = [await td.inner_text() for td in tds]
            c1, c2, c3, c4 = _parse_corners(texts[2] if len(texts) > 2 else "")

            timing = TimingData(
                ranking=_safe_int(texts[0]),
                horse_number=_safe_int(texts[1]),
                corner_pass=texts[2].strip() if len(texts) > 2 else "",
                corner_1=c1,
                corner_2=c2,
                corner_3=c3,
                corner_4=c4,
                s1f=_safe_float(texts[3]) if len(texts) > 3 else None,
                g3f=_safe_float(texts[7]) if len(texts) > 7 else None,
                g1f=_safe_float(texts[9]) if len(texts) > 9 else None,
                split_3f_g=_safe_float(texts[10]) if len(texts) > 10 else None,
                split_1f_g=_safe_float(texts[11]) if len(texts) > 11 else None,
                record_full=texts[12].strip() if len(texts) > 12 else "",
            )
            timings.append(timing)
        break

    return timings


async def crawl_race_result(
    page: Page, track_code: str, rc_date: str, rc_no: int
) -> RaceResult | None:
    """단일 경주 성적 크롤링 (브라우저 재사용)"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    try:
        await _goto_race_result_page(page, meet, rc_date, str(rc_no))

        info = await _parse_race_header(page)
        info.race_date = rc_date
        info.track_code = track_code.upper()
        info.race_number = rc_no

        entries = await _parse_result_entries(page)
        timings = await _parse_timing_entries(page)

        if not entries:
            logger.warning(f"No entries for {track_code} {rc_date} {rc_no}R")
            return None

        result = RaceResult(info=info, entries=entries, timings=timings)
        logger.info(
            f"Result: {track_code} {rc_date} {rc_no}R — "
            f"{len(entries)} entries, {len(timings)} timings"
        )
        return result
    except Exception as e:
        logger.error(f"Error crawling result {track_code} {rc_date} {rc_no}R: {e}")
        return None


async def crawl_race_day_results(
    track_code: str, rc_date: str, max_races: int = 12
) -> list[RaceResult]:
    """하루 전체 경주 성적 크롤링"""
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            for rc_no in range(1, max_races + 1):
                result = await crawl_race_result(page, track_code, rc_date, rc_no)
                if result:
                    results.append(result)
                else:
                    # 결과 없으면 더 이상 경주 없을 수 있음
                    if rc_no > 3:
                        break
        finally:
            await browser.close()

    logger.info(f"Day results: {track_code} {rc_date} — {len(results)} races")
    return results


# ──────────────────────── Race Card (출마표) ────────────────────────

async def _goto_race_card_page(page: Page, meet: str, rc_date: str, rc_no: str):
    """출마표 상세 페이지로 이동"""
    url = (
        f"{KRA_BASE}/chulmainfo/chulmaDetailInfoChulmapyo.do"
        f"?Act=02&Sub=1&meet={meet}&rcNo={rc_no}&rcDate={rc_date}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)


async def _parse_card_header(page: Page) -> RaceInfo:
    """출마표 헤더에서 경주 정보 추출"""
    info = RaceInfo(race_date="", track_code="", race_number=0)

    # 경주 정보 영역 파싱
    all_text = await page.inner_text("body")

    # 거리 추출
    dist_match = re.search(r"(\d{3,4})\s*[mM미]", all_text)
    if dist_match:
        info.distance = int(dist_match.group(1))

    # 등급 추출
    level_match = re.search(r"(\d+)\s*급", all_text)
    if level_match:
        info.race_level = level_match.group(1)

    # 날씨
    weather_match = re.search(r"날씨\s*[:\s]*(\S+)", all_text)
    if weather_match:
        info.weather = weather_match.group(1)

    # 주로상태/함수율
    moisture_match = re.search(r"(?:함수율|주로상태)\s*[:\s]*(\S+)", all_text)
    if moisture_match:
        info.moisture = moisture_match.group(1)

    # 상금 추출
    prize_matches = re.findall(r"(\d{1,3}(?:,\d{3})+)\s*(?:천원|만원)?", all_text)
    prizes = [_parse_prize_text(m) for m in prize_matches if _parse_prize_text(m) > 1000]
    if len(prizes) >= 1:
        info.prize_1st = prizes[0]
    if len(prizes) >= 2:
        info.prize_2nd = prizes[1]
    if len(prizes) >= 3:
        info.prize_3rd = prizes[2]

    return info


async def _parse_card_entries(page: Page) -> list[EntryData]:
    """출마표 출주마 테이블 파싱"""
    entries = []
    tables = await page.query_selector_all("table")

    for table in tables:
        rows = await table.query_selector_all("tbody tr")
        if len(rows) < 3:
            continue

        # 출마표 테이블 감지: 마번, 마명, 기수 등 컬럼 확인
        header_row = await table.query_selector("thead tr")
        if not header_row:
            continue
        headers = await header_row.query_selector_all("th")
        header_texts = [(await h.inner_text()).strip() for h in headers]
        header_joined = " ".join(header_texts)

        if "마번" not in header_joined and "마명" not in header_joined:
            continue

        for row in rows:
            tds = await row.query_selector_all("td")
            if len(tds) < 5:
                continue
            texts = [await td.inner_text() for td in tds]

            # hrNo, jkNo, trNo 추출
            horse_id = ""
            jockey_id = ""
            trainer_id = ""
            links = await row.query_selector_all("a")
            for link in links:
                onclick = await link.get_attribute("onclick") or ""
                href = await link.get_attribute("href") or ""
                combined = onclick + href
                hr_match = re.search(r"hrNo[='\"](\d+)", combined)
                jk_match = re.search(r"jkNo[='\"](\d+)", combined)
                tr_match = re.search(r"trNo[='\"](\d+)", combined)
                if hr_match:
                    horse_id = hr_match.group(1)
                if jk_match:
                    jockey_id = jk_match.group(1)
                if tr_match:
                    trainer_id = tr_match.group(1)

            entry = EntryData(
                horse_number=_safe_int(texts[0]),
                horse_name=texts[1].strip() if len(texts) > 1 else "",
                horse_id=horse_id,
                jockey_name=texts[2].strip() if len(texts) > 2 else "",
                jockey_id=jockey_id,
                trainer_name=texts[3].strip() if len(texts) > 3 else "",
                trainer_id=trainer_id,
                weight=texts[4].strip() if len(texts) > 4 else "",
                rating=_safe_int(texts[5]) if len(texts) > 5 else None,
                age=_safe_int(texts[6]) if len(texts) > 6 else None,
                origin=texts[7].strip() if len(texts) > 7 else "",
                gender=texts[8].strip() if len(texts) > 8 else "",
                recent_record=texts[9].strip() if len(texts) > 9 else "",
            )
            entries.append(entry)
        break

    return entries


async def crawl_race_card(
    page: Page, track_code: str, rc_date: str, rc_no: int
) -> RaceCard | None:
    """단일 경주 출마표 크롤링"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    try:
        await _goto_race_card_page(page, meet, rc_date, str(rc_no))

        info = await _parse_card_header(page)
        info.race_date = rc_date
        info.track_code = track_code.upper()
        info.race_number = rc_no

        entries = await _parse_card_entries(page)
        if not entries:
            logger.warning(f"No card entries for {track_code} {rc_date} {rc_no}R")
            return None

        info.total_entries = len(entries)
        card = RaceCard(info=info, entries=entries)
        logger.info(f"Card: {track_code} {rc_date} {rc_no}R — {len(entries)} entries")
        return card
    except Exception as e:
        logger.error(f"Error crawling card {track_code} {rc_date} {rc_no}R: {e}")
        return None


async def crawl_race_day_cards(
    track_code: str, rc_date: str, max_races: int = 12
) -> list[RaceCard]:
    """하루 전체 출마표 크롤링"""
    cards = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            for rc_no in range(1, max_races + 1):
                card = await crawl_race_card(page, track_code, rc_date, rc_no)
                if card:
                    cards.append(card)
                else:
                    if rc_no > 3:
                        break
        finally:
            await browser.close()

    logger.info(f"Day cards: {track_code} {rc_date} — {len(cards)} races")
    return cards


# ──────────────────────── Entry Changes (출전변경) ────────────────────────

async def crawl_entry_changes(
    track_code: str, rc_date: str
) -> list[EntryChange]:
    """출전변경 페이지 크롤링 — 기수교체, 출전취소 등 감지"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    url = (
        f"{KRA_BASE}/raceFastreport/ChulmapyoChange.do"
        f"?Act=03&Sub=1&meet={meet}"
    )
    changes = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)

            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await table.query_selector_all("tbody tr")
                for row in rows:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 4:
                        continue
                    texts = [await td.inner_text() for td in tds]

                    # 변경 내용 파싱 (사이트 포맷에 따라 조정 필요)
                    change = EntryChange(
                        race_date=rc_date,
                        track_code=track_code.upper(),
                    )
                    content = " ".join(texts).strip()

                    # 기수변경 감지
                    jockey_match = re.search(
                        r"(\d+)R.*기수.*변경.*?(\S+)\s*→\s*(\S+)", content
                    )
                    if jockey_match:
                        change.race_number = int(jockey_match.group(1))
                        change.change_type = "jockey_change"
                        change.field_name = "jockey_name"
                        change.old_value = jockey_match.group(2)
                        change.new_value = jockey_match.group(3)
                        changes.append(change)
                        continue

                    # 출전취소 감지
                    scratch_match = re.search(
                        r"(\d+)R.*(?:출전취소|제외).*?(\S+)", content
                    )
                    if scratch_match:
                        change.race_number = int(scratch_match.group(1))
                        change.change_type = "horse_scratch"
                        change.field_name = "horse_name"
                        change.old_value = scratch_match.group(2)
                        changes.append(change)
                        continue

        finally:
            await browser.close()

    logger.info(f"Changes: {track_code} {rc_date} — {len(changes)} changes detected")
    return changes


# ──────────────────────── Horse Profile (경주마 프로필) ────────────────────────

async def crawl_horse_profile(
    page: Page, horse_id: str, meet: str = "1"
) -> HorseProfile | None:
    """경주마 프로필 크롤링 (세션 필요 — 먼저 출마표 페이지 로드 후 사용)"""
    try:
        # 자바스크립트 폼 제출로 프로필 페이지 이동
        await page.evaluate(f"""
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '/racehorse/profileHorseItem.do';
            var hrNoInput = document.createElement('input');
            hrNoInput.name = 'hrNo';
            hrNoInput.value = '{horse_id}';
            form.appendChild(hrNoInput);
            var meetInput = document.createElement('input');
            meetInput.name = 'meet';
            meetInput.value = '{meet}';
            form.appendChild(meetInput);
            document.body.appendChild(form);
            form.submit();
        """)
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(1)

        profile = HorseProfile(horse_id=horse_id)

        # 프로필 정보 추출
        body_text = await page.inner_text("body")

        name_match = re.search(r"마명\s*[:\s]*(\S+)", body_text)
        if name_match:
            profile.name = name_match.group(1)

        origin_match = re.search(r"산지\s*[:\s]*(\S+)", body_text)
        if origin_match:
            profile.origin = origin_match.group(1)

        gender_match = re.search(r"성별\s*[:\s]*(\S+)", body_text)
        if gender_match:
            profile.gender = gender_match.group(1)

        sire_match = re.search(r"부마\s*[:\s]*(\S+)", body_text)
        if sire_match:
            profile.sire = sire_match.group(1)

        dam_match = re.search(r"모마\s*[:\s]*(\S+)", body_text)
        if dam_match:
            profile.dam = dam_match.group(1)

        owner_match = re.search(r"마주\s*[:\s]*(\S+)", body_text)
        if owner_match:
            profile.owner = owner_match.group(1)

        trainer_match = re.search(r"조교사\s*[:\s]*(\S+)", body_text)
        if trainer_match:
            profile.trainer = trainer_match.group(1)

        logger.info(f"Horse profile: {profile.name} ({horse_id})")
        return profile
    except Exception as e:
        logger.error(f"Error crawling horse profile {horse_id}: {e}")
        return None


# ──────────────────────── Jockey List (기수 목록) ────────────────────────

async def crawl_jockey_list(track_code: str = "S") -> list[JockeyInfo]:
    """기수 목록 크롤링"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    url = f"{KRA_BASE}/jockey/ProfileJockeyListActive.do?Act=09&Sub=1&meet={meet}"
    jockeys = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)

            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await table.query_selector_all("tbody tr")
                if len(rows) < 3:
                    continue
                for row in rows:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 5:
                        continue
                    texts = [await td.inner_text() for td in tds]

                    # jkNo 추출
                    jockey_id = ""
                    link = await row.query_selector("a")
                    if link:
                        onclick = await link.get_attribute("onclick") or ""
                        id_match = re.search(r"['\"](\d{6})['\"]", onclick)
                        if id_match:
                            jockey_id = id_match.group(1)

                    jockey = JockeyInfo(
                        jockey_id=jockey_id,
                        name=texts[1].strip() if len(texts) > 1 else "",
                        debut_date=texts[2].strip() if len(texts) > 2 else "",
                    )

                    # 금년 전적 파싱 (출전-1-2-3 형식)
                    if len(texts) > 3:
                        year_parts = texts[3].replace(" ", "").split("-")
                        if len(year_parts) >= 4:
                            jockey.year_starts = _safe_int(year_parts[0]) or 0
                            jockey.year_wins = _safe_int(year_parts[1]) or 0
                            jockey.year_seconds = _safe_int(year_parts[2]) or 0
                            jockey.year_thirds = _safe_int(year_parts[3]) or 0

                    # 통산 전적 파싱
                    if len(texts) > 4:
                        total_parts = texts[4].replace(" ", "").split("-")
                        if len(total_parts) >= 4:
                            jockey.total_starts = _safe_int(total_parts[0]) or 0
                            jockey.total_wins = _safe_int(total_parts[1]) or 0
                            jockey.total_seconds = _safe_int(total_parts[2]) or 0
                            jockey.total_thirds = _safe_int(total_parts[3]) or 0

                    if len(texts) > 5:
                        jockey.weight = texts[5].strip()

                    jockeys.append(jockey)
                break

        finally:
            await browser.close()

    logger.info(f"Jockeys: {track_code} — {len(jockeys)} jockeys")
    return jockeys


# ──────────────────────── Trainer List (조교사 목록) ────────────────────────

async def crawl_trainer_list(track_code: str = "S") -> list[TrainerInfo]:
    """조교사 목록 크롤링"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    url = f"{KRA_BASE}/trainer/profileTrainerList.do?Act=10&Sub=1&meet={meet}"
    trainers = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)

            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await table.query_selector_all("tbody tr")
                if len(rows) < 3:
                    continue
                for row in rows:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 3:
                        continue
                    texts = [await td.inner_text() for td in tds]

                    trainer_id = ""
                    link = await row.query_selector("a")
                    if link:
                        onclick = await link.get_attribute("onclick") or ""
                        id_match = re.search(r"['\"](\d{6})['\"]", onclick)
                        if id_match:
                            trainer_id = id_match.group(1)

                    trainer = TrainerInfo(
                        trainer_id=trainer_id,
                        name=texts[1].strip() if len(texts) > 1 else "",
                    )
                    trainers.append(trainer)
                break

        finally:
            await browser.close()

    logger.info(f"Trainers: {track_code} — {len(trainers)} trainers")
    return trainers


# ──────────────────────── Race Schedule (경주 일정) ────────────────────────

async def crawl_race_schedule(track_code: str, rc_date: str) -> list[dict]:
    """특정 날짜의 경주 일정 크롤링 (경주 수 / 발주시각 등)"""
    meet = MEET_CODES.get(track_code.upper(), "1")
    url = (
        f"{KRA_BASE}/chulmainfo/ChulmaDetailInfoList.do"
        f"?Act=02&Sub=1&meet={meet}&rcDate={rc_date}"
    )
    races = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)

            tables = await page.query_selector_all("table")
            for table in tables:
                rows = await table.query_selector_all("tbody tr")
                for row in rows:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 4:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    rc_match = re.search(r"(\d+)", texts[0])
                    if rc_match:
                        races.append({
                            "race_number": int(rc_match.group(1)),
                            "raw": texts,
                        })

        finally:
            await browser.close()

    logger.info(f"Schedule: {track_code} {rc_date} — {len(races)} races")
    return races
