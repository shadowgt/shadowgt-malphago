"""검빛(Gumbit) 크롤러 - Playwright async 기반

사이트 분석(2026-04-03) 기반 신규 작성.
기존 Selenium 방식에서 Playwright async로 통일.

크롤링 대상 페이지:
1. 기록비교 (chulma_record.html) — S1F/G1F 구간기록, 거리별 비교
2. 경주력분석 (horse_power_anal.html) — 다경주 이력 + 구간기록 + 마체중
3. 상금전적 (chulma_prize.html) — 경주마/기수/조교사/마주 상금통계
4. 출전및인기도 (chulma_detail.html) — 레이팅, 전적, 인기도, 전문가 예상
5. 기수 상세 (jockey.html) — 6개월 전적 + 상금 + 경주이력
6. 조교사 상세 (trainer.html) — 복승율 + 관리마필 + 경주이력

URL 파라미터:
- loc: S=서울, B=부산, J=제주
- type: 5=평일(부산), 6=토요일, 7=일요일
- m_date: YYYY-MM-DD
- race_no: 경주 회차
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

GUMBIT_BASE = "http://www.gumvit.com"


# ──────────────────────── Dataclasses ────────────────────────

@dataclass
class RecordComparison:
    """기록비교 — 출주마별 구간기록 비교 데이터"""
    horse_number: int | None = None
    horse_name: str = ""
    recent_date: str = ""         # 최근 출전일
    total_starts: int | None = None
    track_condition: str = ""     # 주로상태 (건/양/포/다)
    jockey_name: str = ""
    weight: str = ""
    # 평균 구간기록
    avg_s1f: float | None = None       # S~1F 평균
    avg_g1f: float | None = None       # G~1F 평균
    avg_3c_pos: float | None = None    # 3코너 평균 순위
    avg_4c_pos: float | None = None    # 4코너 평균 순위
    avg_g3f: float | None = None       # G3F 평균
    avg_finish: float | None = None    # 착점 평균
    # 최고 구간기록
    best_s1f: float | None = None
    best_g1f: float | None = None
    # 거리별 기록 (dict: distance_m -> {avg_s1f, avg_g1f})
    distance_records: dict = field(default_factory=dict)


@dataclass
class RacePowerEntry:
    """경주력분석 — 출주마별 과거 경주 이력"""
    horse_name: str = ""
    trainer_name: str = ""
    jockey_name: str = ""
    weight: str = ""
    # 과거 경주 이력 리스트
    history: list[dict] = field(default_factory=list)
    # history 각 항목: {race_date, horse_number, grade, distance,
    #   jockey, weight, ranking, track_pct, horse_weight,
    #   s1f, g3f, g1f, record, power_rating}


@dataclass
class PrizeStats:
    """상금전적 — 4개 테이블 통합"""
    # 경주마 상금
    horse_prizes: list[dict] = field(default_factory=list)
    # {horse_number, horse_name, score, total_record, total_prize, year_record, year_prize}

    # 기수 전적
    jockey_stats: list[dict] = field(default_factory=list)
    # {horse_number, jockey_name, total_record, recent_3m_record, month_record, prize}

    # 조교사 상금
    trainer_stats: list[dict] = field(default_factory=list)
    # {horse_number, trainer_name, avg_1y_prize, avg_6m_prize, monthly_prizes, monthly_record}

    # 마주 상금
    owner_stats: list[dict] = field(default_factory=list)
    # {horse_number, owner_name, avg_1y_prize, avg_6m_prize, horses_count, today_entries}


@dataclass
class EntryPopularity:
    """출전및인기도 데이터"""
    horse_number: int | None = None
    horse_name: str = ""
    rating: int | None = None
    jockey_name: str = ""
    trainer_name: str = ""
    owner_name: str = ""
    record: str = ""              # 전적
    popularity_rank: int | None = None  # 인기도 순위
    expert_pick: str = ""         # 전문가 예상 (★◎○▲)


@dataclass
class JockeyDetail:
    """기수 상세 정보"""
    jockey_id: str = ""           # jkCd
    name: str = ""
    affiliation: str = ""         # 소속조
    debut_date: str = ""
    # 전적
    total_record: str = ""        # 통산전적 (출전-1-2-3)
    year_record: str = ""         # 최근1년
    recent_3m_record: str = ""    # 최근3개월
    month_record: str = ""        # 당월전적
    # 6개월 월별 전적
    monthly_stats: list[dict] = field(default_factory=list)
    # {month, starts, wins, seconds, thirds, prize}
    # 경주이력
    race_history: list[dict] = field(default_factory=list)
    # {race_date, horse_name, ranking, popularity, grade, distance, race_type, trainer, owner}


@dataclass
class TrainerDetail:
    """조교사 상세 정보"""
    trainer_id: str = ""          # trCd
    name: str = ""
    affiliation: str = ""
    birth_year: str = ""
    managed_horses: int = 0       # 관리마수
    # 전적
    total_record: str = ""
    year_record: str = ""
    recent_3m_record: str = ""
    month_record: str = ""
    double_win_rate: float | None = None  # 복승율
    avg_prize: str = ""           # 평균상금
    # 6개월 월별 전적
    monthly_stats: list[dict] = field(default_factory=list)
    # 관리마필 현황
    horse_roster: list[dict] = field(default_factory=list)
    # {horse_name, origin, age, gender, grade, stable}
    # 경주이력
    race_history: list[dict] = field(default_factory=list)


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


def _get_day_type(weekday: int) -> str:
    """요일에 따른 type 파라미터 결정. 0=월~6=일"""
    if weekday == 5:
        return "6"  # 토요일
    elif weekday == 6:
        return "7"  # 일요일
    else:
        return "5"  # 평일 (부산)


def _parse_record_cells(texts: list[str], start_idx: int, count: int) -> list[str]:
    """테이블 셀 텍스트 안전하게 추출"""
    return [texts[i].strip() if i < len(texts) else "" for i in range(start_idx, start_idx + count)]


# ──────────────────────── 기록비교 (Record Comparison) ────────────────────────

async def crawl_record_comparison(
    page: Page, loc: str, m_date: str, race_no: int, day_type: str
) -> list[RecordComparison]:
    """기록비교 페이지 크롤링 — S1F/G1F 구간기록 + 거리별 비교

    Args:
        page: Playwright Page (브라우저 재사용)
        loc: 경마장 (S/B/J)
        m_date: 경주일 (YYYY-MM-DD)
        race_no: 경주 회차
        day_type: 요일 타입 (5/6/7)
    """
    url = (
        f"{GUMBIT_BASE}/statv40/chulma_record.html"
        f"?m_date={m_date}&race_no={race_no}&type={day_type}&loc={loc}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)

    records = []
    tables = await page.query_selector_all("table")

    for table in tables:
        rows = await table.query_selector_all("tr")
        if len(rows) < 3:
            continue

        # 기록비교 테이블 감지
        first_row_text = await rows[0].inner_text() if rows else ""
        if "마번" not in first_row_text and "S~1F" not in first_row_text:
            continue

        for row in rows[1:]:  # 헤더 건너뛰기
            tds = await row.query_selector_all("td")
            if len(tds) < 6:
                continue
            texts = [await td.inner_text() for td in tds]

            record = RecordComparison(
                horse_number=_safe_int(texts[0]),
                horse_name=texts[1].strip() if len(texts) > 1 else "",
            )

            # 구간기록 파싱 (테이블 구조에 따라)
            if len(texts) > 4:
                record.avg_s1f = _safe_float(texts[2])
            if len(texts) > 5:
                record.avg_3c_pos = _safe_float(texts[3])
            if len(texts) > 6:
                record.avg_4c_pos = _safe_float(texts[4])
            if len(texts) > 7:
                record.avg_g3f = _safe_float(texts[5])
            if len(texts) > 8:
                record.avg_g1f = _safe_float(texts[6])
            if len(texts) > 9:
                record.avg_finish = _safe_float(texts[7])

            records.append(record)
        break

    # 거리별 기록 블록 파싱
    distance_blocks = await page.query_selector_all("table")
    for block in distance_blocks:
        block_text = await block.inner_text()
        dist_match = re.search(r"(\d{3,4})[mM]", block_text)
        if not dist_match:
            continue
        distance = dist_match.group(1)

        rows = await block.query_selector_all("tr")
        for row in rows[1:]:
            tds = await row.query_selector_all("td")
            if len(tds) < 4:
                continue
            texts = [await td.inner_text() for td in tds]
            horse_num = _safe_int(texts[0])
            if horse_num is None:
                continue

            # 매칭 레코드 찾기
            for rec in records:
                if rec.horse_number == horse_num:
                    rec.distance_records[distance] = {
                        "s1f": _safe_float(texts[2]) if len(texts) > 2 else None,
                        "g1f": _safe_float(texts[3]) if len(texts) > 3 else None,
                    }
                    break

    logger.info(f"Records: {loc} {m_date} {race_no}R — {len(records)} horses")
    return records


# ──────────────────────── 경주력분석 (Race Power Analysis) ────────────────────────

async def crawl_race_power(
    page: Page, loc: str, m_date: str, race_no: int, day_type: str
) -> list[RacePowerEntry]:
    """경주력분석 페이지 크롤링 — 다경주 이력 + S1F/G3F/G1F + 마체중

    이 페이지가 각 출주마의 최근 2-3경주 이력과 구간기록을 제공하는 핵심 페이지.
    """
    url = (
        f"{GUMBIT_BASE}/statv40/horse_power_anal.html"
        f"?m_date={m_date}&race_no={race_no}&type={day_type}&loc={loc}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)

    entries = []
    tables = await page.query_selector_all("table")

    for table in tables:
        rows = await table.query_selector_all("tr")
        if len(rows) < 2:
            continue

        header_text = await rows[0].inner_text() if rows else ""
        if "마명" not in header_text and "경주력" not in header_text:
            continue

        current_entry = None
        for row in rows[1:]:
            tds = await row.query_selector_all("td")
            if not tds:
                continue
            texts = [await td.inner_text() for td in tds]

            # 새 말 행 감지 (마번이 있는 행)
            first_val = texts[0].strip() if texts else ""
            if first_val and _safe_int(first_val) is not None and len(texts) > 3:
                # 이전 entry 저장
                if current_entry and current_entry.horse_name:
                    entries.append(current_entry)

                current_entry = RacePowerEntry(
                    horse_name=texts[1].strip() if len(texts) > 1 else "",
                )
                # 조교사/기수/중량 블록 파싱
                info_text = texts[2].strip() if len(texts) > 2 else ""
                info_lines = info_text.split("\n")
                for line in info_lines:
                    line = line.strip()
                    if not line:
                        continue
                    # 첫 줄: 조교사, 둘째 줄: 기수 등
                    if not current_entry.trainer_name:
                        current_entry.trainer_name = line
                    elif not current_entry.jockey_name:
                        current_entry.jockey_name = line

            # 경주 이력 행 파싱
            if current_entry and len(texts) >= 8:
                race_date = ""
                # 날짜 형식 감지 (YYYY-MM-DD 또는 MM/DD 등)
                for t in texts:
                    if re.match(r"\d{4}[-/]\d{2}[-/]\d{2}", t.strip()):
                        race_date = t.strip()
                        break
                    elif re.match(r"\d{2}[-/]\d{2}", t.strip()):
                        race_date = t.strip()
                        break

                if race_date:
                    history_entry = {
                        "race_date": race_date,
                    }
                    # 나머지 필드 매핑 (위치 기반)
                    remaining = [t.strip() for t in texts if t.strip() != race_date]
                    if len(remaining) > 0:
                        history_entry["horse_number"] = _safe_int(remaining[0])
                    if len(remaining) > 1:
                        history_entry["grade"] = remaining[1]
                    if len(remaining) > 2:
                        history_entry["distance"] = _safe_int(remaining[2])
                    if len(remaining) > 3:
                        history_entry["jockey"] = remaining[3]
                    if len(remaining) > 4:
                        history_entry["weight"] = remaining[4]
                    if len(remaining) > 5:
                        history_entry["ranking"] = _safe_int(remaining[5])
                    if len(remaining) > 6:
                        history_entry["track_pct"] = remaining[6]
                    if len(remaining) > 7:
                        history_entry["horse_weight"] = _safe_int(remaining[7])
                    if len(remaining) > 8:
                        history_entry["s1f"] = _safe_float(remaining[8])
                    if len(remaining) > 9:
                        history_entry["g3f"] = _safe_float(remaining[9])
                    if len(remaining) > 10:
                        history_entry["g1f"] = _safe_float(remaining[10])
                    if len(remaining) > 11:
                        history_entry["record"] = remaining[11]

                    current_entry.history.append(history_entry)

        # 마지막 entry 저장
        if current_entry and current_entry.horse_name:
            entries.append(current_entry)
        break

    logger.info(f"Power: {loc} {m_date} {race_no}R — {len(entries)} horses")
    return entries


# ──────────────────────── 상금전적 (Prize Records) ────────────────────────

async def crawl_prize_stats(
    page: Page, loc: str, m_date: str, race_no: int, day_type: str
) -> PrizeStats:
    """상금전적 페이지 크롤링 — 경주마/기수/조교사/마주 4개 테이블"""
    url = (
        f"{GUMBIT_BASE}/statv40/chulma_prize.html"
        f"?m_date={m_date}&race_no={race_no}&type={day_type}&loc={loc}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)

    stats = PrizeStats()
    tables = await page.query_selector_all("table")

    table_idx = 0
    for table in tables:
        rows = await table.query_selector_all("tr")
        if len(rows) < 2:
            continue

        header_text = await rows[0].inner_text() if rows else ""

        data_rows = []
        for row in rows[1:]:
            tds = await row.query_selector_all("td")
            if len(tds) < 3:
                continue
            texts = [await td.inner_text() for td in tds]
            data_rows.append(texts)

        if "경주마" in header_text or ("마명" in header_text and "상금" in header_text):
            # 경주마 상금 테이블
            for texts in data_rows:
                stats.horse_prizes.append({
                    "horse_number": _safe_int(texts[0]),
                    "horse_name": texts[1].strip() if len(texts) > 1 else "",
                    "score": _safe_int(texts[2]) if len(texts) > 2 else None,
                    "total_record": texts[3].strip() if len(texts) > 3 else "",
                    "total_prize": texts[4].strip() if len(texts) > 4 else "",
                    "year_record": texts[5].strip() if len(texts) > 5 else "",
                    "year_prize": texts[6].strip() if len(texts) > 6 else "",
                })
            table_idx += 1

        elif "기수" in header_text:
            # 기수 전적 테이블
            for texts in data_rows:
                stats.jockey_stats.append({
                    "horse_number": _safe_int(texts[0]),
                    "jockey_name": texts[1].strip() if len(texts) > 1 else "",
                    "total_record": texts[2].strip() if len(texts) > 2 else "",
                    "recent_3m_record": texts[3].strip() if len(texts) > 3 else "",
                    "month_record": texts[4].strip() if len(texts) > 4 else "",
                    "prize": texts[5].strip() if len(texts) > 5 else "",
                })
            table_idx += 1

        elif "조교사" in header_text:
            # 조교사 상금 테이블
            for texts in data_rows:
                stats.trainer_stats.append({
                    "horse_number": _safe_int(texts[0]),
                    "trainer_name": texts[1].strip() if len(texts) > 1 else "",
                    "avg_1y_prize": texts[2].strip() if len(texts) > 2 else "",
                    "avg_6m_prize": texts[3].strip() if len(texts) > 3 else "",
                })
            table_idx += 1

        elif "마주" in header_text:
            # 마주 상금 테이블
            for texts in data_rows:
                stats.owner_stats.append({
                    "horse_number": _safe_int(texts[0]),
                    "owner_name": texts[1].strip() if len(texts) > 1 else "",
                    "avg_1y_prize": texts[2].strip() if len(texts) > 2 else "",
                    "avg_6m_prize": texts[3].strip() if len(texts) > 3 else "",
                })
            table_idx += 1

    logger.info(
        f"Prize: {loc} {m_date} {race_no}R — "
        f"horses={len(stats.horse_prizes)}, jockeys={len(stats.jockey_stats)}, "
        f"trainers={len(stats.trainer_stats)}, owners={len(stats.owner_stats)}"
    )
    return stats


# ──────────────────────── 출전및인기도 (Entry Popularity) ────────────────────────

async def crawl_entry_popularity(
    page: Page, loc: str, m_date: str, race_no: int, day_type: str
) -> list[EntryPopularity]:
    """출전및인기도 페이지 크롤링 — 레이팅, 전적, 인기도, 전문가 예상"""
    url = (
        f"{GUMBIT_BASE}/statv40/chulma_detail.html"
        f"?m_date={m_date}&race_no={race_no}&type={day_type}&loc={loc}"
    )
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)

    entries = []
    tables = await page.query_selector_all("table")

    for table in tables:
        rows = await table.query_selector_all("tr")
        if len(rows) < 3:
            continue
        header_text = await rows[0].inner_text() if rows else ""
        if "마번" not in header_text:
            continue

        for row in rows[1:]:
            tds = await row.query_selector_all("td")
            if len(tds) < 5:
                continue
            texts = [await td.inner_text() for td in tds]

            entry = EntryPopularity(
                horse_number=_safe_int(texts[0]),
                horse_name=texts[1].strip() if len(texts) > 1 else "",
                rating=_safe_int(texts[2]) if len(texts) > 2 else None,
                jockey_name=texts[3].strip() if len(texts) > 3 else "",
                trainer_name=texts[4].strip() if len(texts) > 4 else "",
                record=texts[5].strip() if len(texts) > 5 else "",
            )

            # 전문가 예상 (★◎○▲ 문자)
            for t in texts:
                if any(c in t for c in "★◎○▲△"):
                    entry.expert_pick = t.strip()
                    break

            entries.append(entry)
        break

    logger.info(f"Popularity: {loc} {m_date} {race_no}R — {len(entries)} horses")
    return entries


# ──────────────────────── 기수 상세 (Jockey Detail) ────────────────────────

async def crawl_jockey_detail(
    page: Page, jockey_id: str, loc: str = "S"
) -> JockeyDetail | None:
    """기수 상세 페이지 크롤링 — 6개월 전적 + 상금 + 경주이력"""
    url = f"{GUMBIT_BASE}/statv40/jockey.html?jkCd={jockey_id}&loc={loc}"
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        detail = JockeyDetail(jockey_id=jockey_id)

        # 기본 정보 추출
        body_text = await page.inner_text("body")
        name_match = re.search(r"기수명\s*[:\s]*(\S+)", body_text)
        if name_match:
            detail.name = name_match.group(1)

        affil_match = re.search(r"소속조\s*[:\s]*(\S+)", body_text)
        if affil_match:
            detail.affiliation = affil_match.group(1)

        # 테이블 파싱
        tables = await page.query_selector_all("table")
        for table in tables:
            rows = await table.query_selector_all("tr")
            if len(rows) < 2:
                continue
            header_text = await rows[0].inner_text() if rows else ""

            # 전적 테이블
            if "통산" in header_text or "전적" in header_text:
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    texts = [await td.inner_text() for td in tds]
                    row_text = " ".join(texts)
                    if "통산" in row_text:
                        detail.total_record = texts[-1].strip() if texts else ""
                    elif "최근1년" in row_text or "1년" in row_text:
                        detail.year_record = texts[-1].strip() if texts else ""
                    elif "3개월" in row_text:
                        detail.recent_3m_record = texts[-1].strip() if texts else ""
                    elif "당월" in row_text:
                        detail.month_record = texts[-1].strip() if texts else ""

            # 월별 전적+상금 테이블
            elif "월" in header_text and ("전적" in header_text or "상금" in header_text):
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 3:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    detail.monthly_stats.append({
                        "month": texts[0].strip(),
                        "record": texts[1].strip() if len(texts) > 1 else "",
                        "prize": texts[2].strip() if len(texts) > 2 else "",
                    })

            # 경주이력 테이블
            elif "경주일" in header_text or "기승마" in header_text:
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 7:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    detail.race_history.append({
                        "race_date": texts[0].strip(),
                        "horse_name": texts[1].strip() if len(texts) > 1 else "",
                        "ranking": _safe_int(texts[2]) if len(texts) > 2 else None,
                        "popularity": _safe_int(texts[3]) if len(texts) > 3 else None,
                        "grade": texts[4].strip() if len(texts) > 4 else "",
                        "distance": _safe_int(texts[5]) if len(texts) > 5 else None,
                        "race_type": texts[6].strip() if len(texts) > 6 else "",
                        "trainer": texts[7].strip() if len(texts) > 7 else "",
                        "owner": texts[8].strip() if len(texts) > 8 else "",
                    })

        logger.info(
            f"Jockey: {detail.name} ({jockey_id}) — "
            f"{len(detail.monthly_stats)} months, {len(detail.race_history)} races"
        )
        return detail
    except Exception as e:
        logger.error(f"Error crawling jockey {jockey_id}: {e}")
        return None


# ──────────────────────── 조교사 상세 (Trainer Detail) ────────────────────────

async def crawl_trainer_detail(
    page: Page, trainer_id: str, loc: str = "S"
) -> TrainerDetail | None:
    """조교사 상세 페이지 크롤링 — 복승율, 관리마필, 경주이력"""
    url = f"{GUMBIT_BASE}/statv40/trainer.html?trCd={trainer_id}&loc={loc}"
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        detail = TrainerDetail(trainer_id=trainer_id)

        body_text = await page.inner_text("body")

        name_match = re.search(r"조교사명?\s*[:\s]*(\S+)", body_text)
        if name_match:
            detail.name = name_match.group(1)

        affil_match = re.search(r"소속조\s*[:\s]*(\S+)", body_text)
        if affil_match:
            detail.affiliation = affil_match.group(1)

        dwr_match = re.search(r"복승율\s*[:\s]*([\d.]+)", body_text)
        if dwr_match:
            detail.double_win_rate = _safe_float(dwr_match.group(1))

        horses_match = re.search(r"관리마\s*[:\s]*(\d+)", body_text)
        if horses_match:
            detail.managed_horses = _safe_int(horses_match.group(1)) or 0

        # 테이블 파싱
        tables = await page.query_selector_all("table")
        for table in tables:
            rows = await table.query_selector_all("tr")
            if len(rows) < 2:
                continue
            header_text = await rows[0].inner_text() if rows else ""

            # 관리마필 현황
            if "마필" in header_text and "현황" in header_text:
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 3:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    detail.horse_roster.append({
                        "horse_name": texts[0].strip(),
                        "origin": texts[1].strip() if len(texts) > 1 else "",
                        "age": _safe_int(texts[2]) if len(texts) > 2 else None,
                        "gender": texts[3].strip() if len(texts) > 3 else "",
                        "grade": texts[4].strip() if len(texts) > 4 else "",
                    })

            # 월별 전적+상금 테이블
            elif "월" in header_text and ("전적" in header_text or "상금" in header_text):
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 3:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    detail.monthly_stats.append({
                        "month": texts[0].strip(),
                        "record": texts[1].strip() if len(texts) > 1 else "",
                        "prize": texts[2].strip() if len(texts) > 2 else "",
                    })

            # 경주이력 테이블
            elif "경주일" in header_text:
                for row in rows[1:]:
                    tds = await row.query_selector_all("td")
                    if len(tds) < 6:
                        continue
                    texts = [await td.inner_text() for td in tds]
                    detail.race_history.append({
                        "race_date": texts[0].strip(),
                        "horse_name": texts[1].strip() if len(texts) > 1 else "",
                        "ranking": _safe_int(texts[2]) if len(texts) > 2 else None,
                        "popularity": _safe_int(texts[3]) if len(texts) > 3 else None,
                        "grade": texts[4].strip() if len(texts) > 4 else "",
                        "distance": _safe_int(texts[5]) if len(texts) > 5 else None,
                    })

        logger.info(
            f"Trainer: {detail.name} ({trainer_id}) — "
            f"horses={len(detail.horse_roster)}, races={len(detail.race_history)}"
        )
        return detail
    except Exception as e:
        logger.error(f"Error crawling trainer {trainer_id}: {e}")
        return None


# ──────────────────────── 경주결과 상세 (Result Detail) ────────────────────────

@dataclass
class RaceResultDetail:
    """검빗 경주결과 상세"""
    race_date: str = ""
    loc: str = ""
    race_no: int = 0
    weather: str = ""
    track_condition: str = ""
    moisture_pct: str = ""
    grade: str = ""
    distance: int = 0
    prize_1st: str = ""
    # 출주마별 결과
    entries: list[dict] = field(default_factory=list)
    # {ranking, horse_number, horse_name, margin, horse_weight,
    #  odds_win, odds_place, s1f, corner_1-4, g3f, g1f, record}


async def crawl_result_detail(
    page: Page, loc: str, race_date: str, race_no: int
) -> RaceResultDetail | None:
    """경주결과 상세 페이지 크롤링 — 구간기록 + 배당 + 코너순위"""
    url = (
        f"{GUMBIT_BASE}/statv40/result_detail.html"
        f"?loc={loc}&racedate={race_date}&race={race_no}"
    )
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        result = RaceResultDetail(race_date=race_date, loc=loc, race_no=race_no)

        body_text = await page.inner_text("body")

        # 경주 정보 추출
        weather_match = re.search(r"날씨\s*[:\s]*(\S+)", body_text)
        if weather_match:
            result.weather = weather_match.group(1)
        moisture_match = re.search(r"함수율\s*[:\s]*([\d.]+)", body_text)
        if moisture_match:
            result.moisture_pct = moisture_match.group(1)
        dist_match = re.search(r"(\d{3,4})\s*[mM]", body_text)
        if dist_match:
            result.distance = int(dist_match.group(1))

        # 결과 테이블 파싱
        tables = await page.query_selector_all("table")
        for table in tables:
            rows = await table.query_selector_all("tr")
            if len(rows) < 3:
                continue
            header_text = await rows[0].inner_text() if rows else ""
            if "순위" not in header_text and "착순" not in header_text:
                continue

            for row in rows[1:]:
                tds = await row.query_selector_all("td")
                if len(tds) < 6:
                    continue
                texts = [await td.inner_text() for td in tds]

                entry = {
                    "ranking": _safe_int(texts[0]),
                    "horse_number": _safe_int(texts[1]),
                    "horse_name": texts[2].strip() if len(texts) > 2 else "",
                    "margin": texts[3].strip() if len(texts) > 3 else "",
                    "horse_weight": _safe_int(texts[4]) if len(texts) > 4 else None,
                    "odds_win": _safe_float(texts[5]) if len(texts) > 5 else None,
                    "odds_place": _safe_float(texts[6]) if len(texts) > 6 else None,
                }

                # 구간기록 (테이블에 있을 경우)
                if len(texts) > 10:
                    entry["s1f"] = _safe_float(texts[7])
                    entry["g3f"] = _safe_float(texts[8])
                    entry["g1f"] = _safe_float(texts[9])
                    entry["record"] = texts[10].strip()

                result.entries.append(entry)
            break

        logger.info(f"Result detail: {loc} {race_date} {race_no}R — {len(result.entries)} entries")
        return result
    except Exception as e:
        logger.error(f"Error crawling result detail {loc} {race_date} {race_no}R: {e}")
        return None


# ──────────────────────── 기수 심층 프로필 (Deep Jockey Profile) ────────────────────

@dataclass
class JockeyDeepProfile:
    """기수 심층 프로필 — 거리별 적성, 이변율, 조교사별 성적"""
    name: str = ""
    loc: str = ""
    double_win_rate: float | None = None    # 복승율
    avg_payout: str = ""                    # 평균배당
    upset_rate: float | None = None         # 인기마 탈락율
    # 거리별 성적
    distance_stats: dict = field(default_factory=dict)
    # {1000: {starts, wins, rate}, 1200: {...}, ...}
    # 조교사별 성적
    trainer_records: list[dict] = field(default_factory=list)
    # {trainer_name, starts, wins, rate}


async def crawl_jockey_deep_profile(
    page: Page, jockey_name: str, loc: str = "S"
) -> JockeyDeepProfile | None:
    """기수 심층 프로필 크롤링 — 거리별/조교사별 분석"""
    import urllib.parse
    encoded_name = urllib.parse.quote(jockey_name)
    url = (
        f"{GUMBIT_BASE}/deep_v40/statv40/jockey/per_jockey.html"
        f"?loc={loc}&jockey={encoded_name}&type=dwin&addtype="
    )
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        profile = JockeyDeepProfile(name=jockey_name, loc=loc)

        body_text = await page.inner_text("body")

        # 복승율
        dwr_match = re.search(r"복승율\s*[:\s]*([\d.]+)", body_text)
        if dwr_match:
            profile.double_win_rate = _safe_float(dwr_match.group(1))

        # 평균배당
        payout_match = re.search(r"평균배당\s*[:\s]*([\d,.]+)", body_text)
        if payout_match:
            profile.avg_payout = payout_match.group(1)

        # 인기마 탈락율
        upset_match = re.search(r"탈락율\s*[:\s]*([\d.]+)", body_text)
        if upset_match:
            profile.upset_rate = _safe_float(upset_match.group(1))

        # 거리별 성적 파싱
        tables = await page.query_selector_all("table")
        for table in tables:
            table_text = await table.inner_text()
            if "거리" not in table_text or "1000" not in table_text:
                continue
            rows = await table.query_selector_all("tr")
            for row in rows[1:]:
                tds = await row.query_selector_all("td")
                if len(tds) < 3:
                    continue
                texts = [await td.inner_text() for td in tds]
                dist_match = re.search(r"(\d{3,4})", texts[0])
                if dist_match:
                    dist = int(dist_match.group(1))
                    profile.distance_stats[dist] = {
                        "starts": _safe_int(texts[1]) if len(texts) > 1 else None,
                        "wins": _safe_int(texts[2]) if len(texts) > 2 else None,
                        "rate": _safe_float(texts[3]) if len(texts) > 3 else None,
                    }
            break

        logger.info(f"Jockey deep: {jockey_name} ({loc}) — {len(profile.distance_stats)} distances")
        return profile
    except Exception as e:
        logger.error(f"Error crawling jockey deep profile {jockey_name}: {e}")
        return None


# ──────────────────────── 통합 크롤링 함수 ────────────────────────

async def crawl_race_analysis(
    loc: str, m_date: str, race_no: int, day_type: str
) -> dict:
    """단일 경주의 검빛 분석 데이터 통합 크롤링

    기록비교 + 경주력분석 + 상금전적 + 인기도를 한번에 수집.

    Returns:
        dict with keys: records, power, prizes, popularity
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            records = await crawl_record_comparison(page, loc, m_date, race_no, day_type)
            power = await crawl_race_power(page, loc, m_date, race_no, day_type)
            prizes = await crawl_prize_stats(page, loc, m_date, race_no, day_type)
            popularity = await crawl_entry_popularity(page, loc, m_date, race_no, day_type)

            return {
                "records": records,
                "power": power,
                "prizes": prizes,
                "popularity": popularity,
            }
        finally:
            await browser.close()


async def crawl_race_day_analysis(
    loc: str, m_date: str, max_races: int = 12, day_type: str = "6"
) -> list[dict]:
    """하루 전체 경주의 검빛 분석 데이터 크롤링"""
    all_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            for race_no in range(1, max_races + 1):
                try:
                    records = await crawl_record_comparison(page, loc, m_date, race_no, day_type)
                    if not records:
                        if race_no > 3:
                            break
                        continue

                    power = await crawl_race_power(page, loc, m_date, race_no, day_type)
                    prizes = await crawl_prize_stats(page, loc, m_date, race_no, day_type)
                    popularity = await crawl_entry_popularity(page, loc, m_date, race_no, day_type)

                    all_data.append({
                        "race_no": race_no,
                        "records": records,
                        "power": power,
                        "prizes": prizes,
                        "popularity": popularity,
                    })
                except Exception as e:
                    logger.error(f"Error crawling analysis {loc} {m_date} {race_no}R: {e}")
                    continue
        finally:
            await browser.close()

    logger.info(f"Day analysis: {loc} {m_date} — {len(all_data)} races")
    return all_data
