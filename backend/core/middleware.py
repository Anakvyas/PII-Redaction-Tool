"""Request-id propagation middleware — every request gets a UUID that shows up
in logs and in the `X-Request-ID` response header, so a client-reported bug can
be traced through the API layer straight to its log lines."""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import get_logger, request_id_ctx

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
