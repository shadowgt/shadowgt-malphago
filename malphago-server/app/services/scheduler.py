"""APScheduler 기반 크롤링 스케줄러

스케줄 (KST):
- 전체 과거기록 크롤링: 주 1회 (월 02:00)
- 출주표 크롤링: 수~금 (10:00)
- 경주일 조기 변경감지: 금/토/일 2시간마다 (06:00~09:00)
- 경주일 실시간 변경감지: 금/토/일 10분마다 (09:00~17:00)
- 경주결과 수집: 금/토/일 (18:00)
- 통계 재계산: 매일 (03:00)
"""

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.crawl_orchestrator import (
    crawl_and_save_race_cards,
    crawl_and_save_results,
    detect_entry_changes,
    crawl_gumbit_analysis,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def _today() -> date:
    return date.today()


def _next_race_dates() -> list[date]:
    """다음 경주일 목록 (금/토/일)"""
    today = _today()
    dates = []
    for i in range(7):
        d = today + timedelta(days=i)
        if d.weekday() in (4, 5, 6):  # 금, 토, 일
            dates.append(d)
    return dates[:3]


# ─── Job Functions ───

async def job_crawl_cards():
    """출주표 크롤링 (수~금 10:00)"""
    race_dates = _next_race_dates()
    for rd in race_dates:
        logger.info(f"[Scheduler] Crawling cards for {rd}")
        await crawl_and_save_race_cards(rd)


async def job_crawl_results():
    """경주결과 수집 (금/토/일 18:00)"""
    today = _today()
    logger.info(f"[Scheduler] Crawling results for {today}")
    await crawl_and_save_results(today)


async def job_detect_changes_early():
    """경주일 조기 변경감지 (06:00~09:00, 2시간마다)"""
    today = _today()
    logger.info(f"[Scheduler] Early change detection for {today}")
    await detect_entry_changes(today)


async def job_detect_changes_realtime():
    """경주일 실시간 변경감지 (09:00~17:00, 10분마다)"""
    today = _today()
    logger.info(f"[Scheduler] Realtime change detection for {today}")
    await detect_entry_changes(today)


async def job_crawl_gumbit():
    """검빛 분석 크롤링 (출주표 후 실행)"""
    race_dates = _next_race_dates()
    for rd in race_dates:
        logger.info(f"[Scheduler] Gumbit analysis for {rd}")
        await crawl_gumbit_analysis(rd)


# ─── Scheduler Setup ───

def setup_scheduler():
    """스케줄러 작업 등록"""

    # 출주표 크롤링: 수~금 10:00
    scheduler.add_job(
        job_crawl_cards,
        CronTrigger(day_of_week="wed-fri", hour=10, minute=0),
        id="crawl_cards",
        replace_existing=True,
    )

    # 경주결과 수집: 금/토/일 18:00
    scheduler.add_job(
        job_crawl_results,
        CronTrigger(day_of_week="fri-sun", hour=18, minute=0),
        id="crawl_results",
        replace_existing=True,
    )

    # 조기 변경감지: 금/토/일 06:00~09:00, 2시간마다
    scheduler.add_job(
        job_detect_changes_early,
        CronTrigger(day_of_week="fri-sun", hour="6-8/2", minute=0),
        id="detect_changes_early",
        replace_existing=True,
    )

    # 실시간 변경감지: 금/토/일 09:00~17:00, 10분마다
    scheduler.add_job(
        job_detect_changes_realtime,
        CronTrigger(day_of_week="fri-sun", hour="9-16", minute="*/10"),
        id="detect_changes_realtime",
        replace_existing=True,
    )

    # 검빛 분석: 수~금 11:00 (출주표 크롤링 후)
    scheduler.add_job(
        job_crawl_gumbit,
        CronTrigger(day_of_week="wed-fri", hour=11, minute=0),
        id="crawl_gumbit",
        replace_existing=True,
    )

    logger.info("[Scheduler] All jobs registered")


def start_scheduler():
    """스케줄러 시작"""
    setup_scheduler()
    scheduler.start()
    logger.info("[Scheduler] Started")


def stop_scheduler():
    """스케줄러 중지"""
    scheduler.shutdown()
    logger.info("[Scheduler] Stopped")
