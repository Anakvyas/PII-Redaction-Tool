"""The detection pipeline: fan out to every registered detector, then resolve
overlapping spans down to a single, confidence-ranked set of entities."""
from __future__ import annotations

from detectors.registry import DetectorRegistry
from schemas.common import ExtractedDocument, PIIEntity, PIIType


class DetectionPipeline:
    def __init__(self, registry: DetectorRegistry) -> None:
        self._registry = registry

    def run(self, document: ExtractedDocument, pii_types: set[PIIType]) -> list[PIIEntity]:
        text = document.flattened_text()
        raw_entities = self._registry.detect_all(text, pii_types)
        return self._merge_overlaps(raw_entities)

    @staticmethod
    def _merge_overlaps(entities: list[PIIEntity]) -> list[PIIEntity]:
        """Greedy interval selection: highest-confidence entity wins any span
        conflict (e.g. a regex SSN match beats a lower-confidence NER guess
        over the same digits); ties break on whichever starts first."""
        ordered = sorted(entities, key=lambda e: (-e.confidence, e.span.start))
        accepted: list[PIIEntity] = []
        for entity in ordered:
            if any(entity.span.overlaps(a.span) for a in accepted):
                continue
            accepted.append(entity)
        return sorted(accepted, key=lambda e: e.span.start)
