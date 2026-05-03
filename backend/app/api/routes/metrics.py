from fastapi import APIRouter, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.core.cache import query_cache
from app.utils.metrics import metrics

router = APIRouter(tags=["metrics"])

QUERY_COUNT = Counter("medgraph_queries_total", "Total queries", ["intent", "llm_status"])
QUERY_LATENCY = Histogram("medgraph_query_latency_seconds", "Query latency")


@router.get("")
@router.get("/")
async def get_metrics(request: Request):
    _ = request
    summary = await metrics.summary()
    cache_stats = await query_cache.stats()
    return {**summary, **cache_stats, "cache": cache_stats}


@router.get("/prometheus")
async def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
