"""DOB detection: date-shaped substrings are cheap to find but ambiguous with
any other date in a document (expiry dates, meeting dates, ...). Confidence is
driven by whether a birth-context keyword appears near the match, not by the
date pattern alone."""
from __future__ import annotations

import re
from datetime import datetime

from detectors.base import BaseDetector
from schemas.common import PIIEntity, PIIType, TextSpan
from utils.ids import new_id
from utils.text import context_window

_MONTHS = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "mdy_slash"),
    (re.compile(r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b"), "mdy_dash"),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd_dash"),
    (re.compile(rf"\b({_MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE), "month_name"),
)

_CONTEXT_KEYWORDS = ("dob", "date of birth", "born", "birth date", "birthdate", "b-day", "birthday")


def _try_parse(match: re.Match, kind: str) -> datetime | None:
    try:
        if kind == "mdy_slash" or kind == "mdy_dash":
            month, day, year = match.groups()
            return datetime(int(year), int(month), int(day))
        if kind == "ymd_dash":
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day))
        if kind == "month_name":
            return datetime.strptime(match.group(), "%B %d, %Y")
    except ValueError:
        try:
            if kind == "month_name":
                return datetime.strptime(match.group().replace(",", ""), "%b %d %Y")
        except ValueError:
            return None
    return None


class DateDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "date_detector"

    def supports(self, pii_type: PIIType) -> bool:
        return pii_type == PIIType.DOB

    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        if PIIType.DOB not in pii_types:
            return []
        now_year = datetime.now().year
        entities: list[PIIEntity] = []
        seen_spans: set[tuple[int, int]] = set()

        for pattern, kind in _PATTERNS:
            for m in pattern.finditer(text):
                if (m.start(), m.end()) in seen_spans:
                    continue
                parsed = _try_parse(m, kind)
                if parsed is None:
                    continue
                if not (now_year - 120 <= parsed.year <= now_year):
                    continue  # not a plausible birth year — likely an expiry/future date

                window = context_window(text, m.start(), m.end())
                has_context = any(keyword in window for keyword in _CONTEXT_KEYWORDS)
                confidence = 0.92 if has_context else 0.4

                seen_spans.add((m.start(), m.end()))
                entities.append(
                    PIIEntity(
                        id=new_id("det"),
                        pii_type=PIIType.DOB,
                        span=TextSpan(start=m.start(), end=m.end()),
                        raw_value=m.group(),
                        confidence=confidence,
                        source_detector=self.name,
                    )
                )
        return entities
