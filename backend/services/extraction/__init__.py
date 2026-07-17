from schemas.common import DocumentFormat
from services.extraction.base import BaseExtractor
from services.extraction.docx_extractor import DocxExtractor
from services.extraction.pdf_extractor import PdfExtractor

_EXTRACTORS: dict[DocumentFormat, BaseExtractor] = {
    DocumentFormat.DOCX: DocxExtractor(),
    DocumentFormat.PDF: PdfExtractor(),
}


def get_extractor(fmt: DocumentFormat) -> BaseExtractor:
    return _EXTRACTORS[fmt]


__all__ = ["BaseExtractor", "DocxExtractor", "PdfExtractor", "get_extractor"]
