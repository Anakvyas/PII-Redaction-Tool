from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.exceptions import NotFoundError
from models.policy import PolicyModel
from schemas.common import PIIType, RedactionStrategy
from schemas.policy import PolicyCreate, PolicyOut, PolicyUpdate
from utils.ids import new_id

DEFAULT_POLICY_ID = "policy_default"


class PolicyService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ensure_default_policy(self) -> None:
        if self._db.get(PolicyModel, DEFAULT_POLICY_ID) is not None:
            return
        record = PolicyModel(
            id=DEFAULT_POLICY_ID,
            name="Default (realistic fake values)",
            strategy_map={t.value: RedactionStrategy.PSEUDONYMIZE.value for t in PIIType},
            confidence_floor=0.75,
        )
        self._db.add(record)
        self._db.commit()

    def create(self, payload: PolicyCreate) -> PolicyOut:
        record = PolicyModel(
            id=new_id("policy"),
            name=payload.name,
            strategy_map={k.value: v.value for k, v in payload.strategy_map.items()},
            confidence_floor=payload.confidence_floor,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return self._to_out(record)

    def update(self, policy_id: str, payload: PolicyUpdate) -> PolicyOut:
        record = self.get(policy_id)
        if payload.name is not None:
            record.name = payload.name
        if payload.strategy_map is not None:
            record.strategy_map = {k.value: v.value for k, v in payload.strategy_map.items()}
        if payload.confidence_floor is not None:
            record.confidence_floor = payload.confidence_floor
        self._db.commit()
        self._db.refresh(record)
        return self._to_out(record)

    def get(self, policy_id: str) -> PolicyModel:
        record = self._db.get(PolicyModel, policy_id)
        if record is None:
            raise NotFoundError(f"Policy '{policy_id}' was not found.")
        return record

    def get_out(self, policy_id: str) -> PolicyOut:
        return self._to_out(self.get(policy_id))

    def list(self) -> list[PolicyOut]:
        records = self._db.query(PolicyModel).order_by(PolicyModel.created_at).all()
        return [self._to_out(r) for r in records]

    @staticmethod
    def _to_out(record: PolicyModel) -> PolicyOut:
        return PolicyOut(
            id=record.id,
            name=record.name,
            strategy_map={PIIType(k): RedactionStrategy(v) for k, v in record.strategy_map.items()},
            confidence_floor=record.confidence_floor,
            created_at=record.created_at,
        )
