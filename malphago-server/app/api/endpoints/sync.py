from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/delta")
async def get_delta(since: datetime = Query(..., description="마지막 동기화 시각 (ISO-8601)")):
    # TODO: 증분 동기화 구현
    return {"since": since.isoformat(), "changes": []}
