"""Structured logging + a request-id context var threaded through every log line."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

from config.settings import get_settings

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | req=%(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonFormatter() if settings.LOG_JSON else TextFormatter())
    root.addHandler(handler)

    # keep third-party loggers reasonably quiet
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
