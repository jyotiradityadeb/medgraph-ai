from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class MedGraphException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class EmbeddingError(MedGraphException):
    def __init__(self, msg: str, details: dict[str, Any] | None = None):
        super().__init__(msg, "EMBEDDING_ERROR", 503, details)


class GraphTraversalError(MedGraphException):
    def __init__(self, msg: str, details: dict[str, Any] | None = None):
        super().__init__(msg, "GRAPH_ERROR", 503, details)


class VectorSearchError(MedGraphException):
    def __init__(self, msg: str, details: dict[str, Any] | None = None):
        super().__init__(msg, "VECTOR_SEARCH_ERROR", 503, details)


class LLMError(MedGraphException):
    def __init__(self, msg: str, details: dict[str, Any] | None = None):
        super().__init__(msg, "LLM_ERROR", 503, details)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


async def medgraph_exception_handler(_request: Request, exc: MedGraphException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": _timestamp(),
        },
    )


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": {"fields": exc.errors()},
            "timestamp": _timestamp(),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = str(uuid.uuid4())
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "details": {"request_id": request_id},
            "timestamp": _timestamp(),
        },
    )
