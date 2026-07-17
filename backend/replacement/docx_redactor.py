"""DOCX redaction: rewrites text inside python-docx Run objects in place,
preserving every run's formatting/style — only the text content changes.
Walks the document with the exact same traversal `services/extraction/docx_extractor.py`
used, so the character offsets computed here always match the ones detection ran against."""
from __future__ import annotations

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from services.extraction.docx_extractor import iter_docx_runs
from replacement.strategies import resolve_replacement


def redact_docx(
    source_path: str,
    output_path: str,
    entities: list[PIIEntity],
    strategy_map: dict[PIIType, RedactionStrategy],
) -> dict[PIIType, int]:
    import docx

    document = docx.Document(source_path)
    ordered_entities = sorted(entities, key=lambda e: e.span.start)
    consistency_map: dict[str, str] = {}
    counters: dict[PIIType, int] = {}
    counts_by_type: dict[PIIType, int] = {}
    already_labeled: set[str] = set()

    offset = 0
    for run, text, _para_idx, _run_idx in iter_docx_runs(document):
        block_len = len(text)
        block_end = offset + block_len
        overlapping = [e for e in ordered_entities if e.span.start < block_end and e.span.end > offset]

        if overlapping and run is not None:
            new_text = _apply_replacements(
                text, offset, overlapping, strategy_map, consistency_map, counters, already_labeled
            )
            run.text = new_text
            for entity in overlapping:
                if entity.id not in already_labeled:
                    key = entity.effective_type()
                    counts_by_type[key] = counts_by_type.get(key, 0) + 1
                    already_labeled.add(entity.id)

        offset = block_end

    document.save(output_path)
    return counts_by_type


def _apply_replacements(
    text: str,
    block_offset: int,
    entities: list[PIIEntity],
    strategy_map: dict[PIIType, RedactionStrategy],
    consistency_map: dict[str, str],
    counters: dict[PIIType, int],
    already_labeled: set[str],
) -> str:
    # Apply right-to-left so earlier local indices stay valid as we edit.
    result = text
    for entity in sorted(entities, key=lambda e: e.span.start, reverse=True):
        local_start = max(0, entity.span.start - block_offset)
        local_end = min(len(text), entity.span.end - block_offset)
        if entity.id in already_labeled:
            # Entity was already fully labeled in an earlier run this document
            # traversal already passed — just drop this run's leftover portion.
            replacement = ""
        else:
            strategy = strategy_map.get(entity.effective_type(), RedactionStrategy.MASK)
            replacement = resolve_replacement(entity, strategy, consistency_map, counters)
        result = result[:local_start] + replacement + result[local_end:]
    return result
