"""API key auth. Disabled automatically when settings.API_KEY is unset (local dev)."""
from __future__ import annotations

import secrets

from fastapi import Depends, Header, Query

from config.settings import Settings, get_settings
from core.exceptions import UnauthorizedError


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    # Browser-native EventSource (used for the job /stream endpoint) can't set
    # custom request headers, so it has no way to send X-API-Key — it can only
    # put the key in the URL. The key is already shipped to the browser as
    # NEXT_PUBLIC_API_KEY, so accepting it as a query param exposes nothing new.
    api_key: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.API_KEY:
        return  # auth disabled — local/dev mode
    supplied = x_api_key or api_key
    # Constant-time comparison — a plain `!=` short-circuits on the first
    # differing byte, which turns response latency into a side channel an
    # attacker can use to recover the key one character at a time.
    if not supplied or not secrets.compare_digest(supplied, settings.API_KEY):
        raise UnauthorizedError("Missing or invalid API key.")
