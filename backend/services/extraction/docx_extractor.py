"""DOCX extraction. `iter_docx_runs` is the single source of truth for
traversal order (body paragraphs, then table cells) — replacement/docx_redactor.py
re-imports it so the character offsets it computes always match extraction's."""
from __future__ import annotations

from collections.abc import Iterator

from services.extraction.base import BaseExtractor
from schemas.common import DocumentFormat, ExtractedDocument, TextBlock


def iter_docx_runs(document) -> Iterator[tuple[object | None, str, int, int | None]]:
    """Yields (run_or_none, text, paragraph_index, run_index) in document order.
    `run` is the live python-docx Run object for real content, and None for the
    synthetic paragraph-break separators — mutate `run.text` in place to redact."""
    para_idx = 0

    def _walk_paragraphs(paragraphs):
        nonlocal para_idx
        for paragraph in paragraphs:
            for run_idx, run in enumerate(paragraph.runs):
                yield run, run.text, para_idx, run_idx
            # Two newlines, not one: gives spaCy's sentencizer a clear
            # paragraph-boundary signal so entities don't bleed across
            # paragraphs (e.g. a name run straight into the next line's label).
            yield None, "\n\n", para_idx, None
            para_idx += 1

    yield from _walk_paragraphs(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from _walk_paragraphs(cell.paragraphs)


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
