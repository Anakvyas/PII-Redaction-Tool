"""DOCX redaction: rewrites text inside python-docx Run objects in place,
preserving every run's formatting/style — only the text content changes.
Walks the document with the exact same traversal `services/extraction/docx_extractor.py`
used, so the character offsets computed here always match the ones detection ran against."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from services.extraction.docx_extractor import iter_docx_runs
from replacement.faker_engine import AuditEntry, FakerReplacementEngine
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
    document.save(output_path)
    return DocxRedactionResult(
        counts_by_type=plan.counts_by_type,
        audit_entries=plan.audit_entries,
        faker_engine=plan.faker_engine,
    )


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
