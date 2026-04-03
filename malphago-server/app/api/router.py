from fastapi import APIRouter

from app.api.endpoints import races, horses, jockeys, predictions, sync

api_router = APIRouter()
api_router.include_router(races.router, prefix="/races", tags=["races"])
api_router.include_router(horses.router, prefix="/horses", tags=["horses"])
api_router.include_router(jockeys.router, prefix="/jockeys", tags=["jockeys"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
