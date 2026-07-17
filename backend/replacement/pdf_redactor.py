"""PDF redaction via PyMuPDF's true redaction annotations: `apply_redactions()`
strips the underlying glyphs from the content stream, it does not merely paint
a box over them — a black rectangle drawn on top of selectable text is a
well-known real-world redaction failure and is deliberately not what this does."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from services.extraction.pdf_extractor import iter_pdf_word_blocks
from replacement.faker_engine import AuditEntry, FakerReplacementEngine, build_audit_entry
from replacement.engine import plan_replacements

_BLACK = (0, 0, 0)
_WHITE = (1, 1, 1)


@dataclass(frozen=True)
class PdfRedactionResult:
    counts_by_type: dict[PIIType, int]
    audit_entries: list[AuditEntry]
    faker_engine: FakerReplacementEngine


def redact_pdf(
    source_path: str,
    output_path: str,
    entities: list[PIIEntity],
    strategy_map: dict[PIIType, RedactionStrategy],
) -> PdfRedactionResult:
    import fitz

    blocks = iter_pdf_word_blocks(source_path)
    source_text = "".join(block.text for block in blocks)
    plan = plan_replacements(
        entities, source_text, strategy_map, black_box_as_empty=True
    )

    doc = fitz.open(source_path)
    try:
        touched_pages: set[int] = set()
        redacted_counts: dict[PIIType, int] = {}
        audit_entries: list[AuditEntry] = []
        for replacement in plan.replacements:
            entity = replacement.entity
            overlapping = [
                b
                for b in blocks
                if b.bbox is not None
                and b.char_offset < entity.span.end
                and entity.span.start < b.char_offset + len(b.text)
            ]
            if not overlapping:
                continue

            label = replacement.replacement

            for i, block in enumerate(overlapping):
                page = doc[block.page]
                rect = fitz.Rect(*block.bbox)
                annot_text = label if i == 0 and label else ""
                page.add_redact_annot(
                    rect, text=annot_text, fill=_BLACK, text_color=_WHITE, fontsize=8
                )
                touched_pages.add(block.page)

            key = entity.effective_type()
            redacted_counts[key] = redacted_counts.get(key, 0) + 1
            audit_entries.append(build_audit_entry(entity, replacement.replacement))

        for page_index in touched_pages:
            doc[page_index].apply_redactions()

        doc.save(output_path)
    finally:
        doc.close()

    return PdfRedactionResult(
        counts_by_type=redacted_counts,
        audit_entries=audit_entries,
        faker_engine=plan.faker_engine,
    )
