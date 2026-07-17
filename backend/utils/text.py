from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """NFKC normalization only — deliberately does not change string length in
    ways that would invalidate character offsets computed by the extractors."""
    return unicodedata.normalize("NFKC", text)


def context_window(text: str, start: int, end: int, radius: int = 40) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].lower()


_PRECEDING_WORD = re.compile(r"([A-Za-z]+)\s*$")


def preceding_word(text: str, start: int, max_lookback: int = 20) -> str:
    """The single word immediately before `start`, skipping trailing
    whitespace — e.g. used to check for "the"/"our"/"this" right before an
    entity candidate (a legal-document defined-term capitalization
    convention: "the Offer for Sale", "our Board of Directors")."""
    window = text[max(0, start - max_lookback) : start]
    match = _PRECEDING_WORD.search(window)
    return match.group(1) if match else ""
