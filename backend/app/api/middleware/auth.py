import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

_EXEMPT_PATHS = {"/health"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()
        configured_key = settings.API_KEY
        if not configured_key:
            return await call_next(request)

        incoming_key = request.headers.get("X-API-Key", "")
        if not incoming_key or not hmac.compare_digest(incoming_key, configured_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
