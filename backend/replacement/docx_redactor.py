"""DOCX redaction: rewrites text inside python-docx Run objects in place,
preserving every run's formatting/style — only the text content changes.
Walks the document with the exact same traversal `services/extraction/docx_extractor.py`
used, so the character offsets computed here always match the ones detection ran against.

Also OCRs every embedded image (see services/image_pii_service.py) and
black-boxes any PII text found in it — a scanned ID card pasted into a
DOCX is still redacted, not just PII in the document's own text runs."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from services.extraction.docx_extractor import iter_docx_runs
from replacement.faker_engine import AuditEntry, FakerReplacementEngine, build_audit_entry
from replacement.engine import PlannedReplacement, plan_replacements


@dataclass(frozen=True)
class DocxRedactionResult:
    counts_by_type: dict[PIIType, int]
    audit_entries: list[AuditEntry]
    faker_engine: FakerReplacementEngine


class _RunSegment:
    def __init__(self, run: object | None, text: str, offset: int) -> None:
        self.run = run
        self.text = text
        self.offset = offset
        self.end = offset + len(text)


def redact_docx(
    source_path: str,
    output_path: str,
    entities: list[PIIEntity],
    strategy_map: dict[PIIType, RedactionStrategy],
    confidence_floor: float = 0.75,
) -> DocxRedactionResult:
    import docx

    document = docx.Document(source_path)
    segments: list[_RunSegment] = []
    offset = 0
    for run, text, _para_idx, _run_idx in iter_docx_runs(document):
        if text:
            segments.append(_RunSegment(run=run, text=text, offset=offset))
            offset += len(text)

    source_text = "".join(segment.text for segment in segments)
    plan = plan_replacements(entities, source_text, strategy_map)
    _apply_planned_replacements(segments, plan.replacements)

    image_counts, image_audit_entries = _redact_images(document, strategy_map, confidence_floor, plan.faker_engine)
    counts_by_type = dict(plan.counts_by_type)
    for pii_type, count in image_counts.items():
        counts_by_type[pii_type] = counts_by_type.get(pii_type, 0) + count

    document.save(output_path)
    return DocxRedactionResult(
        counts_by_type=counts_by_type,
        audit_entries=[*plan.audit_entries, *image_audit_entries],
        faker_engine=plan.faker_engine,
    )


def _redact_images(
    document: object,
    strategy_map: dict[PIIType, RedactionStrategy],
    confidence_floor: float,
    faker_engine: FakerReplacementEngine,
) -> tuple[dict[PIIType, int], list[AuditEntry]]:
    """OCR every embedded image, detect PII in its text via the same
    detection pipeline everything else uses, and black-box the matching
    word regions in place. Soft-fails to a no-op if Tesseract isn't
    installed — this is a bonus capability on top of the guaranteed text
    redaction above, not something that should fail the whole job.

    Scope: black-boxes OCR-detected *text* only. A face photo on an ID
    card is left untouched — that needs a face detector, not implemented
    here."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return {}, []

    from docx.parts.image import ImagePart

    from core.container import get_detection_pipeline
    from replacement.strategies import resolve_replacement
    from services.image_pii_service import build_ocr_document, ocr_image, redact_image_bytes, words_overlapping_span

    counts: dict[PIIType, int] = {}
    audit_entries: list[AuditEntry] = []
    pipeline = get_detection_pipeline()
    requested_types = set(strategy_map)

    for part in list(document.part.related_parts.values()):
        if not isinstance(part, ImagePart):
            continue
        # part.filename falls back to a generic "image.png"/"image.jpeg" for
        # any image that didn't preserve an original name — in a document
        # with several such images that collides and makes them
        # indistinguishable in the audit log. partname (e.g.
        # "/word/media/image4.png") is the part's actual package path and
        # always unique.
        image_id = str(part.partname)
        try:
            text, words = ocr_image(part.blob)
        except Exception:
            continue
        if not text.strip():
            continue

        ocr_document = build_ocr_document(image_id, text)
        detected = pipeline.run(ocr_document, requested_types)
        approved = [e for e in detected if e.is_approved(confidence_floor)]
        if not approved:
            continue

        boxes: list[tuple[int, int, int, int]] = []
        for entity in approved:
            strategy = strategy_map.get(entity.effective_type(), RedactionStrategy.MASK)
            replacement = resolve_replacement(entity, strategy, faker_engine)
            audit_entries.append(build_audit_entry(entity, replacement, image_filename=image_id))
            counts[entity.effective_type()] = counts.get(entity.effective_type(), 0) + 1
            boxes.extend(w.bbox for w in words_overlapping_span(words, entity.span.start, entity.span.end))

        if boxes:
            part._blob = redact_image_bytes(part.blob, boxes)
            part._image = None

    return counts, audit_entries


def _apply_planned_replacements(
    segments: list[_RunSegment],
    replacements: list[PlannedReplacement],
) -> None:
    text_by_run: dict[int, str] = {
        id(segment.run): segment.text
        for segment in segments
        if segment.run is not None
    }

    for replacement in sorted(replacements, key=lambda r: r.entity.span.start, reverse=True):
        span = replacement.entity.span
        overlapping = [
            segment
            for segment in segments
            if segment.run is not None and segment.offset < span.end and span.start < segment.end
        ]
        if not overlapping:
            continue

        for index, segment in enumerate(overlapping):
            run_id = id(segment.run)
            local_start = max(0, span.start - segment.offset)
            local_end = min(len(segment.text), span.end - segment.offset)
            inserted = replacement.replacement if index == 0 else ""
            current = text_by_run[run_id]
            text_by_run[run_id] = current[:local_start] + inserted + current[local_end:]

    for segment in segments:
        if segment.run is not None:
            segment.run.text = text_by_run[id(segment.run)]
