"""Deterministic, format-anchored detectors: SSN, credit card, phone, email,
IP address, and street address. High precision by construction — these types
have fixed shapes, so a model would only add latency and false negatives."""
from __future__ import annotations

import re

from detectors.base import BaseDetector
from schemas.common import PIIEntity, PIIType, TextSpan
from utils.ids import new_id
from utils.validators import is_valid_ipv4, luhn_is_valid

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

_CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\b"
)
_IPV6 = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b")

_STREET_SUFFIX = (
    r"Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|"
    r"Way|Place|Pl|Square|Sq|Terrace|Ter|Circle|Cir|Highway|Hwy"
)
_ADDRESS = re.compile(
    # Several suffix abbreviations (Ter, Dr, St, Rd, Ct, Pl, Sq, Cir...) are
    # short enough to also be the first three-ish letters of an unrelated
    # word ("Term", "Drought", ...) — (?![a-zA-Z]) after the optional period
    # rejects that, the same class of fix as _COMPANY_SUFFIX in
    # detection_service.py. Regression: "2023 Short Term Borrowings" was
    # matching "2023 Short Ter" as a street address ("Ter" from "Term").
    rf"\b\d{{1,6}}\s+[A-Z][A-Za-z]*(?:\s[A-Z][A-Za-z]*){{0,3}}\s(?:{_STREET_SUFFIX})\.?(?![a-zA-Z])"
    rf"(?:,\s*[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*)?"
    rf"(?:,?\s*[A-Z]{{2}})?"
    # Postal code: US ZIP is 5 digits (+4 optional); many other countries
    # (India's PIN, for one) use 6 — match 4-6 so the tail isn't chopped off
    # mid-digit-run, which would otherwise fail the word-boundary safety
    # check downstream and silently drop the whole address.
    rf"(?:\s+\d{{4,6}}(?:-\d{{4}})?)?"
)

_CONFIDENCE = {
    PIIType.SSN: 0.97,
    PIIType.CREDIT_CARD: 0.9,
    PIIType.PHONE: 0.85,
    PIIType.EMAIL: 0.97,
    # Just above spaCy's fixed 0.8 ORG confidence — a validated dotted-quad is
    # more specific than a generic "this looks like an org name" guess (e.g.
    # spaCy tagging "IP 192.168.1.15" as a company), so ties should go to the
    # deterministic match.
    PIIType.IP_ADDRESS: 0.83,
    # A full structural match (street number + name + suffix, usually with
    # city/state/zip) is a highly specific pattern — rank it above spaCy's
    # generic ORG/PERSON guesses so it wins the overlap-merge in
    # DetectionPipeline when, e.g., "Evergreen Terrace" also looks like a
    # plausible company name to the NER model.
    PIIType.ADDRESS: 0.88,
}


class RegexDetector(BaseDetector):
    _SUPPORTED = frozenset(_CONFIDENCE)

    @property
    def name(self) -> str:
        return "regex_detector"

    def supports(self, pii_type: PIIType) -> bool:
        return pii_type in self._SUPPORTED

    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        entities: list[PIIEntity] = []
        if PIIType.SSN in pii_types:
            entities.extend(self._match(text, _SSN, PIIType.SSN))
        if PIIType.CREDIT_CARD in pii_types:
            entities.extend(self._detect_credit_cards(text))
        if PIIType.PHONE in pii_types:
            entities.extend(self._match(text, _PHONE, PIIType.PHONE))
        if PIIType.EMAIL in pii_types:
            entities.extend(self._match(text, _EMAIL, PIIType.EMAIL))
        if PIIType.IP_ADDRESS in pii_types:
            entities.extend(self._detect_ips(text))
        if PIIType.ADDRESS in pii_types:
            entities.extend(self._match(text, _ADDRESS, PIIType.ADDRESS))
        return entities

    def _match(self, text: str, pattern: re.Pattern, pii_type: PIIType) -> list[PIIEntity]:
        return [
            PIIEntity(
                id=new_id("det"),
                pii_type=pii_type,
                span=TextSpan(start=m.start(), end=m.end()),
                raw_value=m.group(),
                confidence=_CONFIDENCE[pii_type],
                source_detector=self.name,
            )
            for m in pattern.finditer(text)
        ]

    def _detect_credit_cards(self, text: str) -> list[PIIEntity]:
        entities = []
        for m in _CARD_CANDIDATE.finditer(text):
            digits = re.sub(r"[ -]", "", m.group())
            if len(digits) not in (13, 14, 15, 16, 17, 18, 19):
                continue
            if not luhn_is_valid(digits):
                continue
            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=PIIType.CREDIT_CARD,
                    span=TextSpan(start=m.start(), end=m.end()),
                    raw_value=m.group(),
                    confidence=_CONFIDENCE[PIIType.CREDIT_CARD],
                    source_detector=self.name,
                )
            )
        return entities

    def _detect_ips(self, text: str) -> list[PIIEntity]:
        entities = []
        for m in _IPV4.finditer(text):
            if not is_valid_ipv4(m.group()):
                continue
            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=PIIType.IP_ADDRESS,
                    span=TextSpan(start=m.start(), end=m.end()),
                    raw_value=m.group(),
                    confidence=_CONFIDENCE[PIIType.IP_ADDRESS],
                    source_detector=self.name,
                )
            )
        for m in _IPV6.finditer(text):
            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=PIIType.IP_ADDRESS,
                    span=TextSpan(start=m.start(), end=m.end()),
                    raw_value=m.group(),
                    confidence=_CONFIDENCE[PIIType.IP_ADDRESS],
                    source_detector=self.name,
                )
            )
        return entities
