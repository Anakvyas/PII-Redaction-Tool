"""OCR-based PII detection and in-place redaction for images embedded in a
document (e.g. a scanned ID card, a screenshot of a form). Reuses the exact
same detection pipeline every other PII type goes through — once OCR turns
an image's pixels into words with bounding boxes, it's just another text
source with a coordinate system attached.

Scope: black-boxes the OCR-detected *text* regions only (name, DOB, ID
numbers, addresses, ...). A face photo on an ID card is not detected or
redacted — that needs a face detector, a separate capability not
implemented here."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from schemas.common import DocumentFormat, ExtractedDocument, TextBlock

# Tesseract's per-word confidence is 0-100; -1 means "no text" (e.g. a
# layout-only region). Below this is usually noise, not a real word.
_MIN_OCR_CONFIDENCE = 40


@dataclass(frozen=True)
class OcrWord:
    text: str
    char_offset: int
    bbox: tuple[int, int, int, int]  # left, top, right, bottom — pixel space


def ocr_image(image_bytes: bytes) -> tuple[str, list[OcrWord]]:
    """OCR the image, returning its reconstructed text (line breaks
    preserved so context-sensitive detectors — e.g. the DOB date heuristic,
    which looks for "date of birth" near a date — still see nearby words)
    and each word's pixel bounding box plus its offset into that text."""
    import pytesseract
    from PIL import Image
    from pytesseract import Output

    image = Image.open(BytesIO(image_bytes))
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    words: list[OcrWord] = []
    text_parts: list[str] = []
    offset = 0
    prev_line_key: tuple[int, int, int] | None = None

    for i, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence < _MIN_OCR_CONFIDENCE:
            continue

        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if prev_line_key is not None:
            separator = "\n" if line_key != prev_line_key else " "
            text_parts.append(separator)
            offset += len(separator)
        prev_line_key = line_key

        left, top, width, height = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append(OcrWord(text=text, char_offset=offset, bbox=(left, top, left + width, top + height)))
        text_parts.append(text)
        offset += len(text)

    return "".join(text_parts), words


def words_overlapping_span(words: list[OcrWord], start: int, end: int) -> list[OcrWord]:
    return [w for w in words if w.char_offset < end and start < w.char_offset + len(w.text)]


def redact_image_bytes(image_bytes: bytes, boxes: list[tuple[int, int, int, int]], padding: int = 2) -> bytes:
    """Black out each box (pixel space) and return the image re-encoded in
    its original format. `padding` grows each box slightly so anti-aliased
    glyph edges don't peek out from under the fill."""
    from PIL import Image, ImageDraw

    image = Image.open(BytesIO(image_bytes))
    fmt = image.format or "PNG"
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    for left, top, right, bottom in boxes:
        draw.rectangle([left - padding, top - padding, right + padding, bottom + padding], fill="black")
    out = BytesIO()
    image.save(out, format=fmt)
    return out.getvalue()


def build_ocr_document(document_id: str, text: str) -> ExtractedDocument:
    """Wrap OCR'd text in the same ExtractedDocument shape the rest of the
    pipeline expects, so the exact same detection pipeline runs over it."""
    return ExtractedDocument(
        document_id=document_id,
        format=DocumentFormat.DOCX,
        blocks=[TextBlock(text=text, char_offset=0)],
    )
