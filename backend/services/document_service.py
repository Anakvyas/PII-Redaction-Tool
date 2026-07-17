from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from config.settings import Settings
from core.exceptions import FileTooLargeError, NotFoundError
from models.document import DocumentModel
from schemas.common import DocumentFormat
from schemas.document import DocumentOut
from services.storage_service import FileStorage
from utils.files import format_from_filename, sha256_of_file
from utils.ids import new_id

_MIME_BY_FORMAT = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


class DocumentService:
    def __init__(self, db: Session, storage: FileStorage, settings: Settings) -> None:
        self._db = db
        self._storage = storage
        self._settings = settings

    def ingest(self, filename: str, tmp_path: str, size_bytes: int) -> DocumentOut:
        if size_bytes > self._settings.MAX_UPLOAD_SIZE_BYTES:
            limit_mb = self._settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise FileTooLargeError(f"File exceeds the {limit_mb}MB upload limit.")

        fmt = format_from_filename(filename, self._settings.ALLOWED_EXTENSIONS)
        checksum = sha256_of_file(tmp_path)

        existing = self._db.query(DocumentModel).filter_by(checksum=checksum).first()
        if existing:
            return self._to_out(existing, deduplicated=True)

        document_id = new_id("doc")
        key = f"originals/{document_id}{Path(filename).suffix.lower()}"
        with open(tmp_path, "rb") as fh:
            storage_uri = self._storage.save(key, fh)

        record = DocumentModel(
            id=document_id,
            filename=filename,
            format=fmt,
            mime_type=_MIME_BY_FORMAT[fmt],
            storage_uri=storage_uri,
            checksum=checksum,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return self._to_out(record, deduplicated=False)

    def get(self, document_id: str) -> DocumentModel:
        record = self._db.get(DocumentModel, document_id)
        if record is None:
            raise NotFoundError(f"Document '{document_id}' was not found.")
        return record

    def get_out(self, document_id: str) -> DocumentOut:
        return self._to_out(self.get(document_id))

    @staticmethod
    def _to_out(record: DocumentModel, deduplicated: bool = False) -> DocumentOut:
        return DocumentOut(
            id=record.id,
            filename=record.filename,
            format=DocumentFormat(record.format),
            mime_type=record.mime_type,
            checksum=record.checksum,
            uploaded_at=record.uploaded_at,
            deduplicated=deduplicated,
        )
