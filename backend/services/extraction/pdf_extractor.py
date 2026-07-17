"""PDF extraction at word granularity via PyMuPDF, so redaction can draw a box
around exactly the words an entity covers rather than a whole paragraph block.
`iter_pdf_word_blocks` is re-used by replacement/pdf_redactor.py so both sides
agree on character offsets and bounding boxes."""
from __future__ import annotations

from services.extraction.base import BaseExtractor
from schemas.common import DocumentFormat, ExtractedDocument, TextBlock


def iter_pdf_word_blocks(file_path: str) -> list[TextBlock]:
    import fitz

    doc = fitz.open(file_path)
    try:
        blocks: list[TextBlock] = []
        offset = 0
        page_count = len(doc)
        for page_index in range(page_count):
            page = doc[page_index]
            words = page.get_text("words")
            words.sort(key=lambda w: (w[5], w[6], w[7]))

            prev_block_no: int | None = None
            prev_line_key: tuple[int, int] | None = None
            for x0, y0, x1, y1, word, block_no, line_no, word_no in words:
                line_key = (block_no, line_no)
                if prev_line_key is not None:
                    if block_no != prev_block_no:
                        # New text block: a real paragraph gap, not a soft
                        # line-wrap — give the NER sentencizer a clear signal
                        # so entities don't bleed across unrelated fields.
                        separator = "\n\n"
                    elif line_key != prev_line_key:
                        separator = "\n"
                    else:
                        separator = " "
                    blocks.append(TextBlock(text=separator, char_offset=offset, page=page_index))
                    offset += len(separator)
                blocks.append(
                    TextBlock(
                        text=word,
                        char_offset=offset,
                        page=page_index,
                        bbox=(x0, y0, x1, y1),
                    )
                )
                offset += len(word)
                prev_line_key = line_key
                prev_block_no = block_no

            if page_index < page_count - 1:
                blocks.append(TextBlock(text="\n\n", char_offset=offset, page=page_index))
                offset += 2
        return blocks
    finally:
        doc.close()


class PdfExtractor(BaseExtractor):
    @property
    def format(self) -> DocumentFormat:
        return DocumentFormat.PDF

    def extract(self, file_path: str, document_id: str) -> ExtractedDocument:
        blocks = iter_pdf_word_blocks(file_path)
        return ExtractedDocument(document_id=document_id, format=self.format, blocks=blocks)
