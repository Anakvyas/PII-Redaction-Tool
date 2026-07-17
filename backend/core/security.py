"""API key auth. Disabled automatically when settings.API_KEY is unset (local dev)."""
from __future__ import annotations

import secrets

from fastapi import Depends, Header

from config.settings import Settings, get_settings
from core.exceptions import UnauthorizedError


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.API_KEY:
        return  # auth disabled — local/dev mode
    # Constant-time comparison — a plain `!=` short-circuits on the first
    # differing byte, which turns response latency into a side channel an
    # attacker can use to recover the key one character at a time.
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.API_KEY):
        raise UnauthorizedError("Missing or invalid API key.")
