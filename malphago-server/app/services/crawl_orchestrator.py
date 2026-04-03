"""크롤링 오케스트레이터

KRA + Gumbit 크롤링을 조합하여 실행하는 고수준 서비스.
APScheduler에서 호출하거나 수동 실행 가능.

스케줄링 패턴:
- 전체 과거기록 크롤링: 주 1회 (월 02:00)
- 출주표 크롤링: 수~금 (10:00)
- 경주일 변경감지 (조기): 금/토/일 2시간마다 (06:00~09:00)
- 경주일 실시간 변경감지: 금/토/일 10분마다 (09:00~17:00)
- 경주결과 수집: 금/토/일 (18:00)
- 통계 재계산: 매일 (03:00)
"""

import logging
from datetime import date, datetime, timedelta

from app.db.session import async_session
from app.crawlers import kra_crawler, gumbit_crawler
from app.services.crawl_storage import (
    save_race_day_results, save_race_day_cards, save_entry_changes,
)

logger = logging.getLogger(__name__)

TRACKS = ["S", "B"]  # 서울, 부산 (제주는 별도 일정)


def _date_to_str(d: date) -> str:
    """date → YYYYMMDD"""
    return d.strftime("%Y%m%d")


def _date_to_dash(d: date) -> str:
    """date → YYYY-MM-DD (검빛용)"""
    return d.strftime("%Y-%m-%d")


def _get_day_type(d: date) -> str:
    """요일 → 검빛 type 파라미터"""
    wd = d.weekday()
    if wd == 5:
        return "6"
    elif wd == 6:
        return "7"
    return "5"


# ──────────────────────── 출마표 크롤링 ────────────────────────

async def crawl_and_save_race_cards(target_date: date, tracks: list[str] | None = None):
    """출마표 크롤링 + DB 저장

    수~금 10:00에 실행. 경주일 출주표를 미리 수집.
    """
    tracks = tracks or TRACKS
    rc_date = _date_to_str(target_date)

    async with async_session() as session:
        for track_code in tracks:
            logger.info(f"Crawling cards: {track_code} {rc_date}")
            cards = await kra_crawler.crawl_race_day_cards(track_code, rc_date)
            if cards:
                saved = await save_race_day_cards(session, cards)
                logger.info(f"Saved {saved} cards for {track_code} {rc_date}")


# ──────────────────────── 경주결과 크롤링 ────────────────────────

async def crawl_and_save_results(target_date: date, tracks: list[str] | None = None):
    """경주결과 크롤링 + DB 저장

    금/토/일 18:00에 실행. 당일 경주 결과를 수집.
    """
    tracks = tracks or TRACKS
    rc_date = _date_to_str(target_date)

    async with async_session() as session:
        for track_code in tracks:
            logger.info(f"Crawling results: {track_code} {rc_date}")
            results = await kra_crawler.crawl_race_day_results(track_code, rc_date)
            if results:
                saved = await save_race_day_results(session, results)
                logger.info(f"Saved {saved} results for {track_code} {rc_date}")


# ──────────────────────── 변경감지 크롤링 ────────────────────────

async def detect_entry_changes(target_date: date, tracks: list[str] | None = None):
    """출전변경 감지 크롤링

    경주일 당일 10분~2시간 간격으로 실행.
    1. KRA 출전변경 페이지 직접 확인
    2. 출마표 재크롤링 → 기존 데이터와 diff 비교 (save_race_card에서 자동 감지)
    """
    tracks = tracks or TRACKS
    rc_date = _date_to_str(target_date)

    async with async_session() as session:
        for track_code in tracks:
            # 1단계: 출전변경 페이지 크롤링
            logger.info(f"Checking changes: {track_code} {rc_date}")
            changes = await kra_crawler.crawl_entry_changes(track_code, rc_date)
            if changes:
                await save_entry_changes(session, changes)

            # 2단계: 출마표 재크롤링 (자동 diff 감지)
            cards = await kra_crawler.crawl_race_day_cards(track_code, rc_date)
            if cards:
                await save_race_day_cards(session, cards)


# ──────────────────────── 검빛 분석 크롤링 ────────────────────────

async def crawl_gumbit_analysis(target_date: date, tracks: list[str] | None = None):
    """검빛 분석 데이터 크롤링

    출마표 크롤링 후 실행. 기록비교/경주력분석/상금전적/인기도 수집.
    현재는 로그만 출력 (DB 저장은 분석 모델 완성 후 연결)
    """
    tracks = tracks or TRACKS
    m_date = _date_to_dash(target_date)
    day_type = _get_day_type(target_date)

    for track_code in tracks:
        loc = track_code.upper()
        logger.info(f"Crawling Gumbit analysis: {loc} {m_date}")
        try:
            data = await gumbit_crawler.crawl_race_day_analysis(
                loc, m_date, day_type=day_type
            )
            logger.info(f"Gumbit analysis: {loc} {m_date} — {len(data)} races")
            # TODO: 분석 데이터 DB 저장 (jockey_stats, horse_stats 등)
        except Exception as e:
            logger.error(f"Gumbit analysis error {loc} {m_date}: {e}")


# ──────────────────────── 과거기록 일괄 크롤링 ────────────────────────

async def crawl_historical_results(
    start_date: date, end_date: date, tracks: list[str] | None = None
):
    """과거 경주 결과 일괄 크롤링

    주 1회 (월 02:00) 실행. 누락된 과거 기록을 보충.
    """
    tracks = tracks or TRACKS
    current = start_date

    while current <= end_date:
        # 경마는 금/토/일만 개최 (weekday: 4=금, 5=토, 6=일)
        if current.weekday() in (4, 5, 6):
            await crawl_and_save_results(current, tracks)
        current += timedelta(days=1)
