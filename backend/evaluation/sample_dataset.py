"""A small, bundled, synthetic gold-standard set covering all nine PII types.
Every value is fabricated (the credit card number is a well-known Luhn-valid
test number) — this exists so the evaluation pipeline and its API/CI gate are
runnable without requiring a real, sensitive labeled dataset to be sourced first."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import PIIType, TextSpan


@dataclass
class EvaluationCase:
    text: str
    expected: list[tuple[PIIType, TextSpan]]


def _case(text: str, labels: list[tuple[PIIType, str]]) -> EvaluationCase:
    expected: list[tuple[PIIType, TextSpan]] = []
    for pii_type, substring in labels:
        start = text.index(substring)
        expected.append((pii_type, TextSpan(start=start, end=start + len(substring))))
    return EvaluationCase(text=text, expected=expected)


SAMPLE_DATASET: list[EvaluationCase] = [
    _case(
        "Jane Doe works at Initech and can be reached at jane.doe@example.com or 555-123-4567.",
        [
            (PIIType.PERSON, "Jane Doe"),
            (PIIType.COMPANY, "Initech"),
            (PIIType.EMAIL, "jane.doe@example.com"),
            (PIIType.PHONE, "555-123-4567"),
        ],
    ),
    _case(
        "Please mail the form to 742 Evergreen Terrace, Springfield, IL 62704.",
        [(PIIType.ADDRESS, "742 Evergreen Terrace, Springfield, IL 62704")],
    ),
    _case(
        "SSN on file: 234-56-7890. DOB: 03/14/1985.",
        [(PIIType.SSN, "234-56-7890"), (PIIType.DOB, "03/14/1985")],
    ),
    _case(
        "Card ending was charged: 4539148803436467 from IP 192.168.1.15.",
        [(PIIType.CREDIT_CARD, "4539148803436467"), (PIIType.IP_ADDRESS, "192.168.1.15")],
    ),
    _case(
        "Contact John Smith at Globex Corporation, born on January 5, 1990, phone (415) 555-0199.",
        [
            (PIIType.PERSON, "John Smith"),
            (PIIType.COMPANY, "Globex Corporation"),
            (PIIType.DOB, "January 5, 1990"),
            (PIIType.PHONE, "(415) 555-0199"),
        ],
    ),
]
