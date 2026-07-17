from __future__ import annotations

from pydantic import BaseModel

from schemas.common import PIIType, ReviewDecision, TextSpan


class DetectionOut(BaseModel):
    id: str
    pii_type: PIIType
    span: TextSpan
    raw_value: str
    confidence: float
    source_detector: str
    human_verified: bool
    human_decision: ReviewDecision | None
    new_pii_type: PIIType | None = None

    model_config = {"from_attributes": True}


class DetectionReviewUpdate(BaseModel):
    decision: ReviewDecision
    new_pii_type: PIIType | None = None
