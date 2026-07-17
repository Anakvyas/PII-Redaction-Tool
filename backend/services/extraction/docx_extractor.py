"""DOCX extraction.

`iter_docx_runs` is the single source of truth for traversal order. The DOCX
redactor imports it too, so extraction offsets and replacement offsets stay
locked together across the main document body, headers, footers, tables, nested
tables, and hyperlink runs.
"""
from __future__ import annotations

from collections.abc import Iterator

from services.extraction.base import BaseExtractor
from schemas.common import DocumentFormat, ExtractedDocument, TextBlock


_PARAGRAPH_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
_TABLE_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl"


def iter_docx_story_parts(document) -> Iterator[object]:
    """Yield every unique story part whose text should be parsed/redacted."""
    seen_parts: set[int] = set()

    def _yield_once(part: object) -> Iterator[object]:
        part_id = id(getattr(part, "part", part))
        if part_id in seen_parts:
            return
        seen_parts.add(part_id)
        yield part

    yield from _yield_once(document)

    for section in document.sections:
        for attr in (
            "header",
            "first_page_header",
            "even_page_header",
            "footer",
            "first_page_footer",
            "even_page_footer",
        ):
            story = getattr(section, attr, None)
            if story is not None and _story_has_content(story):
                yield from _yield_once(story)


def _iter_block_items(parent: object) -> Iterator[object]:
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph

    if isinstance(parent, _Cell):
        container = parent._tc
    elif hasattr(parent, "element") and hasattr(parent.element, "body"):
        container = parent.element.body
    elif hasattr(parent, "_element"):
        container = parent._element
    else:
        return

    for child in container.iterchildren():
        if child.tag == _PARAGRAPH_TAG:
            yield Paragraph(child, parent)
        elif child.tag == _TABLE_TAG:
            yield Table(child, parent)


def _iter_table_cells(table: object) -> Iterator[object]:
    """Yield unique table cells, skipping the repeats `row.cells` produces
    for a merged span (python-docx reports a merged cell at every grid
    position it covers).

    Tracks the actual `_tc` oxml elements in the set, not `id(cell._tc)` —
    `row.cells` constructs a fresh `_Cell` wrapper on every access, and if
    only the id() is kept, the wrapper is immediately eligible for garbage
    collection; CPython is then free to recycle that exact memory address
    for the *next* cell's wrapper, making two genuinely different cells
    compare equal. Confirmed in production against a real 4-column,
    9-row table: every column-1..3 cell in every data row false-positived
    as a duplicate of an earlier, unrelated cell, silently dropping the
    designation/ID/address of 7 of 8 people from extraction (and therefore
    from redaction) — only column 0 survived. Keeping the elements
    themselves in the set holds a strong reference, so identity remains
    meaningful for the lifetime of the check."""
    seen_cells: set[object] = set()
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            if tc in seen_cells:
                continue
            seen_cells.add(tc)
            yield cell


def _iter_paragraph_runs(paragraph: object) -> Iterator[object]:
    """Yield runs in visual/XML order, including runs inside hyperlinks."""
    iter_inner_content = getattr(paragraph, "iter_inner_content", None)
    if iter_inner_content is None:
        yield from paragraph.runs
        return

    for item in iter_inner_content():
        runs = getattr(item, "runs", None)
        if runs is None:
            yield item
        else:
            yield from runs


def _story_has_content(story_part: object) -> bool:
    for block in _iter_block_items(story_part):
        if hasattr(block, "runs"):
            if any(run.text for run in _iter_paragraph_runs(block)):
                return True
        else:
            for cell in _iter_table_cells(block):
                if _story_has_content(cell):
                    return True
    return False


def iter_docx_runs(document) -> Iterator[tuple[object | None, str, int, int | None]]:
    """Yields (run_or_none, text, paragraph_index, run_index) in document order.
    `run` is the live python-docx Run object for real content, and None for the
    synthetic paragraph-break separators — mutate `run.text` in place to redact."""
    para_idx = 0

    def _walk_parent(parent: object):
        nonlocal para_idx
        for block in _iter_block_items(parent):
            if hasattr(block, "runs"):
                for run_idx, run in enumerate(_iter_paragraph_runs(block)):
                    yield run, run.text, para_idx, run_idx
                # Two newlines, not one: gives sentence/entity detectors a
                # clear paragraph-boundary signal so entities don't bleed
                # across unrelated fields.
                yield None, "\n\n", para_idx, None
                para_idx += 1
            else:
                for cell in _iter_table_cells(block):
                    yield from _walk_parent(cell)

    for story_part in iter_docx_story_parts(document):
        yield from _walk_parent(story_part)


class DocxExtractor(BaseExtractor):
    @property
    def format(self) -> DocumentFormat:
        return DocumentFormat.DOCX

    def extract(self, file_path: str, document_id: str) -> ExtractedDocument:
        import docx

        document = docx.Document(file_path)
        blocks: list[TextBlock] = []
        offset = 0
        for run, text, para_idx, run_idx in iter_docx_runs(document):
            if not text:
                continue
            blocks.append(
                TextBlock(
                    text=text,
                    char_offset=offset,
                    paragraph_index=para_idx,
                    run_index=run_idx,
                )
            )
            offset += len(text)

        return ExtractedDocument(document_id=document_id, format=self.format, blocks=blocks)
