from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    """NFKC normalization only — deliberately does not change string length in
    ways that would invalidate character offsets computed by the extractors."""
    return unicodedata.normalize("NFKC", text)


def context_window(text: str, start: int, end: int, radius: int = 40) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].lower()
