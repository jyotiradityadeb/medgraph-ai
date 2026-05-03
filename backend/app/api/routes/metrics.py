from fastapi import APIRouter, Request

from app.core.cache import query_cache
from app.utils.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get("")
@router.get("/")
async def get_metrics(request: Request):
    _ = request
    summary = await metrics.summary()
    cache_stats = await query_cache.stats()
    return {**summary, **cache_stats, "cache": cache_stats}
