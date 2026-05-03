from __future__ import annotations

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)


class QueryCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._client: aioredis.Redis | None = None

    def _redis(self) -> aioredis.Redis:
        if self._client is None:
            settings = get_settings()
            self._client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._client

    def _key(self, query: str, modalities: list, top_k: int) -> str:
        payload = json.dumps({"q": query.lower().strip(), "m": sorted(modalities), "k": top_k})
        return "qcache:" + hashlib.sha256(payload.encode()).hexdigest()[:16]

    async def get(self, query: str, modalities: list, top_k: int) -> dict | None:
        key = self._key(query, modalities, top_k)
        try:
            val = await self._redis().get(key)
            if val:
                return json.loads(val)
        except Exception as exc:
            logger.warning("cache.get.failed key=%s error=%s", key, exc)
        return None

    async def set(self, query: str, modalities: list, top_k: int, data: dict) -> None:
        key = self._key(query, modalities, top_k)
        try:
            await self._redis().setex(key, self.ttl, json.dumps(data))
        except Exception as exc:
            logger.warning("cache.set.failed key=%s error=%s", key, exc)

    async def stats(self) -> dict:
        try:
            client = self._redis()
            hits = int(await client.get("cache:hits") or 0)
            misses = int(await client.get("cache:misses") or 0)
            total = hits + misses
            keys = await client.keys("qcache:*")
            return {
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hits / total, 3) if total else 0.0,
                "cached_queries": len(keys),
            }
        except Exception as exc:
            logger.warning("cache.stats.failed error=%s", exc)
            return {"hits": 0, "misses": 0, "hit_rate": 0.0, "cached_queries": 0}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


query_cache = QueryCache()
