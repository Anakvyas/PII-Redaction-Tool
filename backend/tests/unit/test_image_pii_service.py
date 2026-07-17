from __future__ import annotations

import shutil

import pytest

pytesseract = pytest.importorskip("pytesseract")
PIL = pytest.importorskip("PIL")

if shutil.which("tesseract") is None:
    pytest.skip("tesseract binary not installed", allow_module_level=True)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from io import BytesIO  # noqa: E402

from services.image_pii_service import (  # noqa: E402
    build_ocr_document,
    ocr_image,
    redact_image_bytes,
    words_overlapping_span,
)


def _render_text_image(lines: list[str], size: tuple[int, int] = (800, 300)) -> bytes:
    # A portable, scalable font (no system font files needed) so OCR quality
    # is consistent across environments/CI.
    font = ImageFont.load_default(size=28)
    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((20, 20 + i * 60), line, fill="black", font=font)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class TestOcrImage:
    def test_extracts_readable_text(self):
        image_bytes = _render_text_image(["Name: Rashi Patil", "Email: rashi.patil@gmail.com"])
        text, words = ocr_image(image_bytes)
        assert "Rashi" in text
        assert "Patil" in text
        assert "rashi.patil@gmail.com" in text
        assert len(words) >= 5

    def test_word_offsets_match_reconstructed_text(self):
        image_bytes = _render_text_image(["Name: Rashi Patil"])
        text, words = ocr_image(image_bytes)
        for word in words:
            assert text[word.char_offset : word.char_offset + len(word.text)] == word.text

    def test_separate_lines_get_a_newline_not_a_space(self):
        image_bytes = _render_text_image(["Name: Rashi Patil", "Phone: 9876543210"])
        text, _words = ocr_image(image_bytes)
        assert "\n" in text

    def test_blank_image_returns_empty_text(self):
        image = Image.new("RGB", (200, 100), color="white")
        buf = BytesIO()
        image.save(buf, format="PNG")
        text, words = ocr_image(buf.getvalue())
        assert text.strip() == ""
        assert words == []


class TestWordsOverlappingSpan:
    def test_returns_words_within_the_span(self):
        image_bytes = _render_text_image(["Rashi Patil works here"])
        text, words = ocr_image(image_bytes)
        start = text.index("Rashi")
        end = start + len("Rashi Patil")
        matched = words_overlapping_span(words, start, end)
        assert [w.text for w in matched] == ["Rashi", "Patil"]

    def test_returns_empty_list_when_nothing_overlaps(self):
        image_bytes = _render_text_image(["Rashi Patil"])
        _text, words = ocr_image(image_bytes)
        assert words_overlapping_span(words, 10_000, 10_010) == []


class TestRedactImageBytes:
    def test_blacks_out_the_given_region(self):
        image_bytes = _render_text_image(["Rashi Patil"])
        _text, words = ocr_image(image_bytes)
        target = words[0]

        redacted_bytes = redact_image_bytes(image_bytes, [target.bbox], padding=0)
        redacted = Image.open(BytesIO(redacted_bytes)).convert("RGB")

        cx = (target.bbox[0] + target.bbox[2]) // 2
        cy = (target.bbox[1] + target.bbox[3]) // 2
        assert redacted.getpixel((cx, cy)) == (0, 0, 0)

    def test_leaves_untouched_regions_alone(self):
        image_bytes = _render_text_image(["Rashi Patil", "Amod Joshi"])
        _text, words = ocr_image(image_bytes)
        first_word = words[0]
        last_word = words[-1]

        redacted_bytes = redact_image_bytes(image_bytes, [first_word.bbox], padding=0)
        redacted = Image.open(BytesIO(redacted_bytes)).convert("RGB")

        # A single pixel at the region's center can legitimately land on a
        # black letter stroke even when untouched — check the whole region
        # isn't a solid black fill (which redaction would produce) instead.
        left, top, right, bottom = last_word.bbox
        _min_value, max_value = redacted.crop((left, top, right, bottom)).convert("L").getextrema()
        assert max_value > 0

    def test_reredacted_image_no_longer_ocrs_the_original_text(self):
        image_bytes = _render_text_image(["Rashi Patil"])
        text, words = ocr_image(image_bytes)
        assert "Patil" in text

        redacted_bytes = redact_image_bytes(image_bytes, [w.bbox for w in words])
        redacted_text, _ = ocr_image(redacted_bytes)
        assert "Patil" not in redacted_text
        assert "Rashi" not in redacted_text


class TestBuildOcrDocument:
    def test_wraps_text_as_a_single_block_extracted_document(self):
        document = build_ocr_document("image.png", "Name: Rashi Patil")
        assert document.document_id == "image.png"
        assert document.flattened_text() == "Name: Rashi Patil"
