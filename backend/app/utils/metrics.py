from __future__ import annotations

import time
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self.query_count = 0
        self.latencies: list[float] = []
        self.error_counts: dict[str, int] = defaultdict(int)
        self.modality_usage: dict[str, int] = defaultdict(int)
        self.graph_depth_usage: list[int] = []
        self.start_time = time.time()

    def record_query(self, latency_ms: float, modalities: list, graph_nodes: int):
        self.query_count += 1
        self.latencies.append(latency_ms)
        if len(self.latencies) > 200:
            self.latencies = self.latencies[-200:]
        for modality in modalities:
            self.modality_usage[modality] += 1
        self.graph_depth_usage.append(graph_nodes)

    def record_error(self, error_type: str):
        self.error_counts[error_type] += 1

    def summary(self) -> dict:
        lat = self.latencies
        recent = lat[-50:]
        p95_idx = int(len(recent) * 0.95) if recent else 0
        return {
            "uptime_seconds": round(time.time() - self.start_time),
            "total_queries": self.query_count,
            "avg_latency_ms": round(sum(recent) / max(len(recent), 1), 1),
            "p95_latency_ms": round(sorted(recent)[p95_idx] if recent else 0, 1),
            "error_counts": dict(self.error_counts),
            "modality_usage": dict(self.modality_usage),
            "avg_graph_nodes": round(
                sum(self.graph_depth_usage[-50:]) / max(len(self.graph_depth_usage[-50:]), 1), 1
            ),
        }


metrics = MetricsCollector()
