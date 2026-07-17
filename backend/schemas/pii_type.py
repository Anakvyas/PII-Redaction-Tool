from __future__ import annotations

from pydantic import BaseModel

from schemas.common import PIIType


class PIITypeInfo(BaseModel):
    pii_type: PIIType
    detectors: list[str]
    example: str
