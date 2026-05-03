"""HIPAA-aligned audit logger for medical queries.

Logs query metadata to audit.log without storing raw query text (PII risk).
Uses SHA-256 hash of the query as the correlation key.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

_audit_logger = logging.getLogger("audit")

if not _audit_logger.handlers:
    _handler = logging.FileHandler("audit.log", encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _audit_logger.addHandler(_handler)
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False


class AuditLogger:
    def log_query(
        self,
        query: str,
        intent: str,
        sources_count: int,
        graph_nodes_count: int,
        llm_status: str,
        processing_time_ms: float,
        extra: dict[str, Any] | None = None,
    ) -> None:
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        record: dict[str, Any] = {
            "event": "query",
            "ts": round(time.time(), 3),
            "query_hash": query_hash,
            "intent": intent,
            "sources_count": sources_count,
            "graph_nodes_count": graph_nodes_count,
            "llm_status": llm_status,
            "processing_time_ms": round(processing_time_ms, 1),
        }
        if extra:
            record.update(extra)
        _audit_logger.info(record)


audit_log = AuditLogger()
