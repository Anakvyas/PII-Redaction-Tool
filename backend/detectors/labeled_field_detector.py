"""Deterministic fallback for full names that generic NER misses in terse
"Label: Value" form contexts (application forms, ticket headers, prospectus
cover pages) — spaCy's statistical PERSON recognition is context-dependent
and empirically inconsistent on exactly this pattern. On the same input,
"Applicant: Rashi Patil" and "Applicant Name: Rashi Patil" both return zero
entities from spaCy/Presidio, while "Rashi Patil applied for the position."
and "Name: Rohan Dey" are both recognized correctly — the failure is about
sentence-less, label-prefixed structure, not the name itself.

This detector doesn't replace NER — it corroborates it when both fire on the
same span (see DetectionPipeline._boost_corroborated) and stands alone as a
recall safety net when NER stays silent. Deliberately excludes bare "Name:"
(too ambiguous — company/product/file name are all common), and filters out
common non-person words (salutation targets like "Dear Customer Service")
that would otherwise match the same capitalized-words shape."""
from __future__ import annotations

import re

from detectors.base import BaseDetector
from schemas.common import PIIEntity, PIIType, TextSpan
from utils.ids import new_id

# Two to four consecutive capitalized words — a full personal name, allowing
# common compounding (hyphens, apostrophes): "Rashi Patil", "Al-Rashid",
# "O'Brien Singh". Requires at least two words so a single capitalized noun
# right after the label ("Applicant: Confidential") doesn't match.
#
# The inter-word gap deliberately uses horizontal whitespace only ([ \t]),
# never \s — \s matches newlines, and a greedy \s+ here would walk straight
# across a paragraph break into the *next* line's label (e.g. "Rashi Patil"
# followed by "\n\nEmail: ..." got swallowed whole as "Rashi Patil Email").
_NAME = r"[A-Z][a-zA-Z'-]+(?:[ \t]+[A-Z][a-zA-Z'-]+){1,3}"

# Safe with an optional colon — specific enough (a full field-label phrase,
# or a salutation opener) that they essentially never form an unrelated
# legal/business compound term with a random capitalized phrase after them.
_OPTIONAL_COLON_LABELS = (
    r"Applicant(?:\s+Name)?",
    r"Customer\s+Name",
    r"Employee\s+Name",
    r"Candidate\s+Name",
    r"Contact(?:\s+Person|\s+Name)?",
    r"Authorized\s+Signatory",
    r"Signed\s+by",
    r"Attention",
    r"Attn",
    r"Dear",
)

# Single generic legal/business-role nouns — regression test: in a real IPO
# prospectus, "Promoter" and "Director" are constantly the first word of an
# unrelated compound term ("Promoter Selling Shareholder", "Director
# Identification Number"), not a "Label: Name" field. Requiring a literal
# colon restricts these to the explicit field form without losing it.
_MANDATORY_COLON_LABELS = (
    r"Promoter",
    r"Director",
    r"Signatory",
    r"Witness",
    r"Guarantor",
)

_LABELED_NAME = re.compile(
    rf"\b(?:"
    rf"(?:{'|'.join(_OPTIONAL_COLON_LABELS)})\s*:?\s*"
    rf"|(?:{'|'.join(_MANDATORY_COLON_LABELS)})\s*:\s*"
    rf")({_NAME})"
)

# Words that fit the "two-plus capitalized words" shape but are never a
# person's name — mostly salutation targets ("Dear Customer Service").
_NON_NAME_WORDS = frozenset(
    {
        "sir", "madam", "team", "service", "services", "department", "support",
        "customer", "customers", "staff", "committee", "board", "management",
        "all", "everyone", "member", "members", "user", "users", "client",
        "clients", "valued", "dear", "hiring", "recruiting", "recruitment",
    }
)

_CONFIDENCE = 0.82


class LabeledFieldDetector(BaseDetector):
    """Structural, label-anchored fallback for PERSON — see module docstring."""

    @property
    def name(self) -> str:
        return "labeled_field_detector"

    def supports(self, pii_type: PIIType) -> bool:
        return pii_type == PIIType.PERSON

    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        if PIIType.PERSON not in pii_types:
            return []

        entities: list[PIIEntity] = []
        for match in _LABELED_NAME.finditer(text):
            candidate = match.group(1)
            if any(token.lower() in _NON_NAME_WORDS for token in candidate.split()):
                continue

            start, end = match.span(1)
            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=PIIType.PERSON,
                    span=TextSpan(start=start, end=end),
                    raw_value=candidate,
                    confidence=_CONFIDENCE,
                    source_detector=self.name,
                )
            )
        return entities
