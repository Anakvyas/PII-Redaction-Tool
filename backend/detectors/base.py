"""Port every detection adapter implements. Adding a tenth PII type or a new
detection engine means writing one class here and registering it in
detectors/registry.py — nothing in the detection pipeline changes."""
from __future__ import annotations

from abc import ABC, abstractmethod

from schemas.common import PIIEntity, PIIType


class BaseDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def supports(self, pii_type: PIIType) -> bool: ...

    @abstractmethod
    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        """Return PIIEntity objects with spans relative to `text`."""
        ...
