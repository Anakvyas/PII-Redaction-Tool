"""Serves local-backend downloads via the signed token `signed_url()` issues.
Deliberately outside the X-API-Key gate — a browser navigating to a download
link can't attach custom headers, so the time-limited signed token in the URL
is the access control here."""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from core.container import get_storage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/download")
async def download_file(token: str = Query(...)) -> FileResponse:
    storage = get_storage()
    local_path = storage.resolve_download(token)
    return FileResponse(local_path)
