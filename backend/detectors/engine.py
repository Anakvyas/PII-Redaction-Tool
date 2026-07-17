"""The PII Detection Engine's public entry point.

Fans out across Presidio (spaCy en_core_web_lg), a second independent spaCy
NER pass, deterministic regex detectors, and RapidFuzz-boosted heuristics;
merges detections, resolves overlaps, assigns a calibrated confidence score,
and normalizes the result to a small, stable contract:

    [{"type": str, "text": str, "start": int, "end": int, "confidence": float}, ...]

This sits on top of DetectionPipeline/DetectorRegistry (the same machinery
the FastAPI app uses for real document jobs) so there is exactly one
detection algorithm in the codebase — this module just exposes it under the
simple contract a caller who isn't the job pipeline wants.
"""
from __future__ import annotations

from core.container import get_detection_pipeline
from schemas.common import DocumentFormat, ExtractedDocument, PIIType, TextBlock


def detect_pii(text: str, pii_types: set[PIIType] | None = None) -> list[dict]:
    """Run the full detection engine over a raw text string.

    `pii_types` restricts which types are searched for; omit it to search for
    all nine supported types. Returns entities in left-to-right order, with
    no two entities overlapping and `text == input_text[start:end]` for every
    result.
    """
    types = pii_types if pii_types is not None else set(PIIType)
    document = ExtractedDocument(
        document_id="engine",
        format=DocumentFormat.DOCX,
        blocks=[TextBlock(text=text, char_offset=0)],
    )
    entities = get_detection_pipeline().run(document, types)
    return [
        {
            "type": entity.pii_type.value,
            "text": entity.raw_value,
            "start": entity.span.start,
            "end": entity.span.end,
            "confidence": entity.confidence,
        }
        for entity in entities
    ]
