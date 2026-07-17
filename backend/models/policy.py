from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PolicyModel(Base):
    __tablename__ = "redaction_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    strategy_map: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_floor: Mapped[float] = mapped_column(Float, default=0.75)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
