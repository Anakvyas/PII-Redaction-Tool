from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from schemas.common import PIIType, RedactionStrategy


class PolicyCreate(BaseModel):
    name: str
    strategy_map: dict[PIIType, RedactionStrategy] = Field(default_factory=dict)
    confidence_floor: float = Field(default=0.75, ge=0.0, le=1.0)


class PolicyUpdate(BaseModel):
    name: str | None = None
    strategy_map: dict[PIIType, RedactionStrategy] | None = None
    confidence_floor: float | None = Field(default=None, ge=0.0, le=1.0)


class PolicyOut(BaseModel):
    id: str
    name: str
    strategy_map: dict[PIIType, RedactionStrategy]
    confidence_floor: float
    created_at: datetime

    model_config = {"from_attributes": True}
