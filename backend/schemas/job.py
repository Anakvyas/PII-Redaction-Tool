from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.common import JobStatus, PIIType
from schemas.detection import DetectionOut


class JobCreate(BaseModel):
    document_id: str
    policy_id: str
    pii_types: list[PIIType] = Field(default_factory=lambda: list(PIIType))


class RedactionSummaryOut(BaseModel):
    counts_by_type: dict[PIIType, int] = Field(default_factory=dict)
    total_redacted: int = 0


class JobOut(BaseModel):
    id: str
    document_id: str
    policy_id: str
    status: JobStatus
    pii_types: list[PIIType]
    error: str | None = None
    summary: RedactionSummaryOut | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobDetailOut(JobOut):
    detections: list[DetectionOut] = Field(default_factory=list)


class DownloadOut(BaseModel):
    url: str
    expires_in: int
