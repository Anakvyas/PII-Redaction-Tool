"""PDF redaction via PyMuPDF's true redaction annotations: `apply_redactions()`
strips the underlying glyphs from the content stream, it does not merely paint
a box over them — a black rectangle drawn on top of selectable text is a
well-known real-world redaction failure and is deliberately not what this does."""
from __future__ import annotations

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from services.extraction.pdf_extractor import iter_pdf_word_blocks
from replacement.strategies import resolve_replacement

_BLACK = (0, 0, 0)
_WHITE = (1, 1, 1)


def redact_pdf(
    source_path: str,
    output_path: str,
    entities: list[PIIEntity],
    strategy_map: dict[PIIType, RedactionStrategy],
) -> dict[PIIType, int]:
    import fitz

    blocks = iter_pdf_word_blocks(source_path)
    consistency_map: dict[str, str] = {}
    counters: dict[PIIType, int] = {}
    counts_by_type: dict[PIIType, int] = {}

    doc = fitz.open(source_path)
    try:
        touched_pages: set[int] = set()
        for entity in entities:
            overlapping = [
                b
                for b in blocks
                if b.bbox is not None
                and b.char_offset < entity.span.end
                and entity.span.start < b.char_offset + len(b.text)
            ]
            if not overlapping:
                continue

            strategy = strategy_map.get(entity.effective_type(), RedactionStrategy.MASK)
            label = (
                ""
                if strategy == RedactionStrategy.BLACK_BOX
                else resolve_replacement(entity, strategy, consistency_map, counters)
            )

            for i, block in enumerate(overlapping):
                page = doc[block.page]
                rect = fitz.Rect(*block.bbox)
                annot_text = label if i == 0 and label else ""
                page.add_redact_annot(
                    rect, text=annot_text, fill=_BLACK, text_color=_WHITE, fontsize=8
                )
                touched_pages.add(block.page)

            key = entity.effective_type()
            counts_by_type[key] = counts_by_type.get(key, 0) + 1

        for page_index in touched_pages:
            doc[page_index].apply_redactions()

        doc.save(output_path)
    finally:
        doc.close()

    return counts_by_type
