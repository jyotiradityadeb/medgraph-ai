from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_START_TIME = time.time()


class MetricsCollector:
    def __init__(self):
        self.query_count = 0
        self.latencies: list[float] = []
        self.error_counts: dict[str, int] = {}
        self.modality_usage: dict[str, int] = {}
        self.graph_depth_usage: list[int] = []
        self.start_time = _START_TIME

    async def record_query(self, latency_ms: float, modalities: list, graph_nodes: int) -> None:
        try:
            self.query_count += 1
            self.latencies.append(float(latency_ms))
            self.latencies = self.latencies[-200:]
            for modality in modalities:
                key = str(modality)
                self.modality_usage[key] = self.modality_usage.get(key, 0) + 1
            self.graph_depth_usage.append(int(graph_nodes))
            self.graph_depth_usage = self.graph_depth_usage[-50:]
        except Exception as exc:
            logger.warning("metrics.record_query.failed error=%s", exc)

    async def record_error(self, error_type: str) -> None:
        try:
            key = str(error_type)
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
        except Exception as exc:
            logger.warning("metrics.record_error.failed error=%s", exc)

    async def summary(self) -> dict:
        try:
            raw_latencies = self.latencies[-50:]
            graph_nodes_list = self.graph_depth_usage[-50:]

            p95_idx = int(len(raw_latencies) * 0.95) if raw_latencies else 0
            avg_latency = round(sum(raw_latencies) / max(len(raw_latencies), 1), 1)
            p95_latency = round(sorted(raw_latencies)[p95_idx] if raw_latencies else 0, 1)
            avg_nodes = round(sum(graph_nodes_list) / max(len(graph_nodes_list), 1), 1)

            return {
                "uptime_seconds": round(time.time() - self.start_time),
                "total_queries": self.query_count,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "error_counts": dict(self.error_counts),
                "modality_usage": dict(self.modality_usage),
                "avg_graph_nodes": avg_nodes,
            }
        except Exception as exc:
            logger.warning("metrics.summary.failed error=%s", exc)
            return {
                "uptime_seconds": round(time.time() - self.start_time),
                "total_queries": 0,
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "error_counts": {},
                "modality_usage": {},
                "avg_graph_nodes": 0,
            }

    async def close(self) -> None:
        pass


metrics = MetricsCollector()
