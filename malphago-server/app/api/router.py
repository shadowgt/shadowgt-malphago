from fastapi import APIRouter

from app.api.endpoints import races, horses, jockeys, predictions, sync, synergy, crawl, analysis

api_router = APIRouter()
api_router.include_router(races.router, prefix="/races", tags=["races"])
api_router.include_router(horses.router, prefix="/horses", tags=["horses"])
api_router.include_router(jockeys.router, prefix="/jockeys", tags=["jockeys"])
api_router.include_router(synergy.router, prefix="/synergy", tags=["synergy"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(crawl.router, prefix="/crawl", tags=["crawl"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
