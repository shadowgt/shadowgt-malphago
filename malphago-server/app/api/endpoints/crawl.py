"""크롤링 수동 트리거 API (관리용)"""

from datetime import date

from fastapi import APIRouter, Query, BackgroundTasks

from app.services.crawl_orchestrator import (
    crawl_and_save_race_cards,
    crawl_and_save_results,
    detect_entry_changes,
    crawl_gumbit_analysis,
)

router = APIRouter()


@router.post("/cards")
async def trigger_crawl_cards(
    target_date: date = Query(..., alias="date"),
    track: str = Query("S", description="경마장 코드 (S/B/J)"),
    background_tasks: BackgroundTasks = None,
):
    """출마표 크롤링 수동 트리거"""
    background_tasks.add_task(crawl_and_save_race_cards, target_date, [track.upper()])
    return {"status": "started", "task": "crawl_cards", "date": target_date.isoformat(), "track": track}


@router.post("/results")
async def trigger_crawl_results(
    target_date: date = Query(..., alias="date"),
    track: str = Query("S", description="경마장 코드 (S/B/J)"),
    background_tasks: BackgroundTasks = None,
):
    """경주결과 크롤링 수동 트리거"""
    background_tasks.add_task(crawl_and_save_results, target_date, [track.upper()])
    return {"status": "started", "task": "crawl_results", "date": target_date.isoformat(), "track": track}


@router.post("/changes")
async def trigger_detect_changes(
    target_date: date = Query(..., alias="date"),
    track: str = Query("S", description="경마장 코드 (S/B/J)"),
    background_tasks: BackgroundTasks = None,
):
    """출전변경 감지 수동 트리거"""
    background_tasks.add_task(detect_entry_changes, target_date, [track.upper()])
    return {"status": "started", "task": "detect_changes", "date": target_date.isoformat(), "track": track}


@router.post("/gumbit")
async def trigger_gumbit_analysis(
    target_date: date = Query(..., alias="date"),
    track: str = Query("S", description="경마장 코드 (S/B/J)"),
    background_tasks: BackgroundTasks = None,
):
    """검빛 분석 크롤링 수동 트리거"""
    background_tasks.add_task(crawl_gumbit_analysis, target_date, [track.upper()])
    return {"status": "started", "task": "gumbit_analysis", "date": target_date.isoformat(), "track": track}
