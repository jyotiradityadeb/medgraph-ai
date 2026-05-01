from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import limiter
from app.core.cache import query_cache
from app.utils.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get("")
@router.get("/")
@limiter.limit("60/minute")
async def get_metrics(request: Request):
    _ = request
    cache_stats = query_cache.stats()
    return {**metrics.summary(), **cache_stats, "cache": cache_stats}
