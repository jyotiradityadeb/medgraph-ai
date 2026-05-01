from __future__ import annotations

import hashlib
import json
import time


class QueryCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        self._cache: dict[str, dict] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _key(self, query: str, modalities: list, top_k: int) -> str:
        payload = json.dumps({"q": query.lower().strip(), "m": sorted(modalities), "k": top_k})
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def get(self, query: str, modalities: list, top_k: int) -> dict | None:
        key = self._key(query, modalities, top_k)
        entry = self._cache.get(key)
        if entry and time.time() - entry["ts"] < self.ttl:
            self.hits += 1
            return entry["data"]
        self.misses += 1
        return None

    def set(self, query: str, modalities: list, top_k: int, data: dict):
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k]["ts"])
            del self._cache[oldest]
        key = self._key(query, modalities, top_k)
        self._cache[key] = {"data": data, "ts": time.time()}

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 3) if total > 0 else 0.0

    def stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "cached_queries": len(self._cache),
        }


query_cache = QueryCache()
