"""The plugin registry — the extension point promised by the architecture.
A new PII type or detection engine is one class implementing BaseDetector,
added to the list passed in here. Nothing else in the app changes."""
from __future__ import annotations

from detectors.base import BaseDetector
from schemas.common import PIIEntity, PIIType


class DetectorRegistry:
    def __init__(self, detectors: list[BaseDetector]) -> None:
        self._detectors = detectors

    def detectors_for(self, pii_type: PIIType) -> list[BaseDetector]:
        return [d for d in self._detectors if d.supports(pii_type)]

    def detect_all(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        """Fan out to every detector that supports at least one requested type."""
        results: list[PIIEntity] = []
        for detector in self._detectors:
            applicable = {t for t in pii_types if detector.supports(t)}
            if applicable:
                results.extend(detector.detect(text, applicable))
        return results

    def catalog(self) -> dict[PIIType, list[str]]:
        return {
            pii_type: [d.name for d in self._detectors if d.supports(pii_type)]
            for pii_type in PIIType
        }
