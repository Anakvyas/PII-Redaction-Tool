from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from api.v1.deps import get_document_service
from schemas.document import DocumentOut
from services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentOut:
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        size_bytes = Path(tmp_path).stat().st_size
        return service.ingest(filename=file.filename or "upload", tmp_path=tmp_path, size_bytes=size_bytes)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str, service: DocumentService = Depends(get_document_service)
) -> DocumentOut:
    return service.get_out(document_id)
