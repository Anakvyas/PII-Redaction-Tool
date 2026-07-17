"""The detection pipeline: fan out to every registered detector, boost
confidence where independent detectors corroborate each other, resolve
overlapping spans down to a single ranked set, then normalize the result."""
from __future__ import annotations

from detectors.registry import DetectorRegistry
from schemas.common import ExtractedDocument, PIIEntity, PIIType, TextSpan
from utils.fuzzy import text_similarity

_TRIM_CHARS = " \t\n\r.,;:!?()[]{}\"'‘’“”"
_CORROBORATION_SIMILARITY = 0.85
_CORROBORATION_BOOST = 0.05
_DETERMINISTIC_SOURCES = frozenset({"regex_detector", "date_detector"})


class DetectionPipeline:
    def __init__(self, registry: DetectorRegistry) -> None:
        self._registry = registry

    def run(self, document: ExtractedDocument, pii_types: set[PIIType]) -> list[PIIEntity]:
        text = document.flattened_text()
        raw_entities = self._registry.detect_all(text, pii_types)
        boosted = self._boost_corroborated(raw_entities)
        merged = self._merge_overlaps(boosted)
        return [self._normalize(e) for e in merged]

    @staticmethod
    def _boost_corroborated(entities: list[PIIEntity]) -> list[PIIEntity]:
        """Two independently-built detectors agreeing on the same span and
        type is a stronger signal than either alone (e.g. Presidio and the
        regex SSN pattern both firing on the same digits) — nudge confidence
        up when that happens, rather than silently discarding the second
        opinion once overlap-resolution picks a single winner."""
        boosted: list[PIIEntity] = []
        for entity in entities:
            corroborated = any(
                other.source_detector != entity.source_detector
                and other.pii_type == entity.pii_type
                and entity.span.overlaps(other.span)
                and text_similarity(entity.raw_value, other.raw_value) >= _CORROBORATION_SIMILARITY
                for other in entities
                if other is not entity
            )
            if corroborated and entity.confidence < 0.99:
                entity = entity.model_copy(
                    update={"confidence": min(0.99, entity.confidence + _CORROBORATION_BOOST)}
                )
            boosted.append(entity)
        return boosted

    @staticmethod
    def _merge_overlaps(entities: list[PIIEntity]) -> list[PIIEntity]:
        """Greedy interval selection: highest-confidence entity wins any span
        conflict (e.g. a regex SSN match beats a lower-confidence NER guess
        over the same digits); ties break on whichever starts first.

        One structural exception: a deterministic, format-anchored match
        (regex/date) that fully *contains* a lower-priority statistical
        fragment of a different type wins regardless of the raw confidence
        gap. This matters in practice — e.g. spaCy and Presidio both
        independently mistaking "Evergreen Terrace" for an ORGANIZATION
        inside a full street address, each corroborating the other's error,
        can otherwise out-rank the correct, more-specific ADDRESS regex
        match that contains it. Containment from a validated pattern is
        strictly more informative than a same-family NER guess over a
        fragment of it, so it overrides ranking by score alone."""
        ordered = sorted(entities, key=lambda e: (-e.confidence, e.span.start))
        accepted: list[PIIEntity] = []
        for entity in ordered:
            conflicts = [a for a in accepted if entity.span.overlaps(a.span)]
            if not conflicts:
                accepted.append(entity)
                continue

            contains_all_conflicts = all(
                c.pii_type != entity.pii_type
                and entity.span.start <= c.span.start
                and c.span.end <= entity.span.end
                for c in conflicts
            )
            if entity.source_detector in _DETERMINISTIC_SOURCES and contains_all_conflicts:
                for conflict in conflicts:
                    accepted.remove(conflict)
                accepted.append(entity)
        return sorted(accepted, key=lambda e: e.span.start)

    @staticmethod
    def _normalize(entity: PIIEntity) -> PIIEntity:
        """Trim incidental punctuation/whitespace off span boundaries (a
        trailing comma or period picked up by a greedy match) and put
        confidence on a clean, consistently-rounded 0-1 scale. Offsets are
        always adjusted in lock-step with the trimmed text, so `text ==
        source[start:end]` remains true for every entity the pipeline returns."""
        value = entity.raw_value
        start, end = entity.span.start, entity.span.end
        while value and value[0] in _TRIM_CHARS:
            value, start = value[1:], start + 1
        while value and value[-1] in _TRIM_CHARS:
            value, end = value[:-1], end - 1

        # confidence is already bounded to [0, 1] by PIIEntity's own field
        # constraint; here we just fix the rounding to a stable precision.
        confidence = round(entity.confidence, 4)

        if not value:
            # Trimming emptied it out (shouldn't happen for real detections,
            # but never return a zero-length span) — keep the original.
            return entity.model_copy(update={"confidence": confidence})

        if value == entity.raw_value and confidence == entity.confidence:
            return entity

        return entity.model_copy(
            update={
                "raw_value": value,
                "span": TextSpan(start=start, end=end, page=entity.span.page, bbox=entity.span.bbox),
                "confidence": confidence,
            }
        )
