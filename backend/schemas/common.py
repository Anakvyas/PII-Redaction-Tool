"""Shared enums + the internal data shapes passed between detectors, services,
and the replacement/evaluation pipelines. Pydantic models double as both the
in-process representation and, where exposed directly, the API schema."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PIIType(str, Enum):
    PERSON = "person"
    EMAIL = "email"
    PHONE = "phone"
    COMPANY = "company"
    ADDRESS = "address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    DOB = "dob"
    IP_ADDRESS = "ip_address"


class RedactionStrategy(str, Enum):
    MASK = "mask"
    PSEUDONYMIZE = "pseudonymize"
    GENERALIZE = "generalize"
    BLACK_BOX = "black_box"


class DocumentFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"


class JobStatus(str, Enum):
    QUEUED = "queued"
    DETECTING = "detecting"
    NEEDS_REVIEW = "needs_review"
    REDACTING = "redacting"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewDecision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    RETYPE = "retype"


class TextSpan(BaseModel):
    start: int
    end: int
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    def overlaps(self, other: "TextSpan") -> bool:
        return self.start < other.end and other.start < self.end

    def __len__(self) -> int:
        return self.end - self.start


class PIIEntity(BaseModel):
    id: str
    pii_type: PIIType
    span: TextSpan
    raw_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_detector: str
    human_verified: bool = False
    human_decision: ReviewDecision | None = None
    new_pii_type: PIIType | None = None  # set when human_decision == RETYPE

    def effective_type(self) -> PIIType:
        return self.new_pii_type if self.human_decision == ReviewDecision.RETYPE and self.new_pii_type else self.pii_type

    def is_approved(self, confidence_floor: float) -> bool:
        if self.human_decision is not None:
            return self.human_decision in (ReviewDecision.ACCEPT, ReviewDecision.RETYPE)
        return self.confidence >= confidence_floor

    def needs_review(self, confidence_floor: float) -> bool:
        return self.human_decision is None and self.confidence < confidence_floor


class TextBlock(BaseModel):
    """A contiguous run of extracted text mapped back to its source location."""

    text: str
    char_offset: int
    page: int | None = None
    paragraph_index: int | None = None
    run_index: int | None = None
    bbox: tuple[float, float, float, float] | None = None


class ExtractedDocument(BaseModel):
    document_id: str
    format: DocumentFormat
    blocks: list[TextBlock]

    def flattened_text(self) -> str:
        return "".join(block.text for block in self.blocks)

    def blocks_overlapping(self, start: int, end: int) -> list[TextBlock]:
        return [
            b for b in self.blocks
            if b.char_offset < end and start < b.char_offset + len(b.text)
        ]
