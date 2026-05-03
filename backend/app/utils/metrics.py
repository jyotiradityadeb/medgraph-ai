from __future__ import annotations

import logging
import time

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_START_TIME = time.time()


class MetricsCollector:
    def __init__(self):
        self._client: aioredis.Redis | None = None

    def _redis(self) -> aioredis.Redis:
        if self._client is None:
            settings = get_settings()
            self._client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._client

    async def record_query(self, latency_ms: float, modalities: list, graph_nodes: int) -> None:
        try:
            r = self._redis()
            pipe = r.pipeline()
            pipe.incr("metrics:query_count")
            pipe.lpush("metrics:latencies", latency_ms)
            pipe.ltrim("metrics:latencies", 0, 199)
            for modality in modalities:
                pipe.hincrby("metrics:modalities", modality, 1)
            pipe.lpush("metrics:graph_nodes", graph_nodes)
            pipe.ltrim("metrics:graph_nodes", 0, 49)
            await pipe.execute()
        except Exception as exc:
            logger.warning("metrics.record_query.failed error=%s", exc)

    async def record_error(self, error_type: str) -> None:
        try:
            await self._redis().hincrby("metrics:errors", error_type, 1)
        except Exception as exc:
            logger.warning("metrics.record_error.failed error=%s", exc)

    async def summary(self) -> dict:
        try:
            r = self._redis()
            pipe = r.pipeline()
            pipe.get("metrics:query_count")
            pipe.lrange("metrics:latencies", 0, 49)
            pipe.hgetall("metrics:errors")
            pipe.hgetall("metrics:modalities")
            pipe.lrange("metrics:graph_nodes", 0, 49)
            results = await pipe.execute()

            query_count = int(results[0] or 0)
            raw_latencies = [float(v) for v in (results[1] or [])]
            error_counts = {k: int(v) for k, v in (results[2] or {}).items()}
            modality_usage = {k: int(v) for k, v in (results[3] or {}).items()}
            graph_nodes_list = [int(v) for v in (results[4] or [])]

            p95_idx = int(len(raw_latencies) * 0.95) if raw_latencies else 0
            avg_latency = round(sum(raw_latencies) / max(len(raw_latencies), 1), 1)
            p95_latency = round(sorted(raw_latencies)[p95_idx] if raw_latencies else 0, 1)
            avg_nodes = round(sum(graph_nodes_list) / max(len(graph_nodes_list), 1), 1)

            return {
                "uptime_seconds": round(time.time() - _START_TIME),
                "total_queries": query_count,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "error_counts": error_counts,
                "modality_usage": modality_usage,
                "avg_graph_nodes": avg_nodes,
            }
        except Exception as exc:
            logger.warning("metrics.summary.failed error=%s", exc)
            return {
                "uptime_seconds": round(time.time() - _START_TIME),
                "total_queries": 0,
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "error_counts": {},
                "modality_usage": {},
                "avg_graph_nodes": 0,
            }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


metrics = MetricsCollector()
