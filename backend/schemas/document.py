from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from schemas.common import DocumentFormat


class DocumentOut(BaseModel):
    id: str
    filename: str
    format: DocumentFormat
    mime_type: str
    checksum: str
    uploaded_at: datetime
    deduplicated: bool = False

    model_config = {"from_attributes": True}
