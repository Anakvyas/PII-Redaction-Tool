from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class DetectionModel(Base):
    __tablename__ = "pii_detections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("redaction_jobs.id"), index=True)
    pii_type: Mapped[str] = mapped_column(String(32), index=True)
    span_start: Mapped[int] = mapped_column(Integer)
    span_end: Mapped[int] = mapped_column(Integer)
    span_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    span_bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source_detector: Mapped[str] = mapped_column(String(64))
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    human_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_pii_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    job: Mapped["JobModel"] = relationship(back_populates="detections")
