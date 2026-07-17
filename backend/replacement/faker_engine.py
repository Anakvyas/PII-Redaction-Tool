"""Faker-backed pseudonymization with stable per-run mappings."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from faker import Faker

from schemas.common import PIIEntity, PIIType


@dataclass(frozen=True)
class MappingEntry:
    pii_type: PIIType
    original: str
    replacement: str


@dataclass(frozen=True)
class AuditEntry:
    entity_id: str
    pii_type: PIIType
    original: str
    replacement: str
    span_start: int
    span_end: int
    page: int | None
    bbox: tuple[float, float, float, float] | None
    source_detector: str
    confidence: float
    # Set only for PII found via OCR inside an embedded image (see
    # services/image_pii_service.py) — span_start/span_end then index into
    # that image's own OCR'd text, not the document's text.
    image_filename: str | None = None


class FakerReplacementEngine:
    """Generates realistic, stable fake values for every supported PII type."""

    def __init__(self) -> None:
        self._faker = Faker(["en_IN", "en_US"])
        self._indian_faker = Faker("en_IN")
        self._mapping: dict[tuple[PIIType, str], str] = {}
        self._used_replacements: set[tuple[PIIType, str]] = set()
        self._person_names: dict[str, str] = {}

    def pseudonymize(self, entity: PIIEntity) -> str:
        pii_type = entity.effective_type()
        original = _clean_original(entity.raw_value)
        key = (pii_type, original)
        if key in self._mapping:
            return self._mapping[key]

        replacement = self._unique_replacement(pii_type, original)
        self._mapping[key] = replacement
        self._used_replacements.add((pii_type, replacement.casefold()))
        return replacement

    def register_static_replacement(self, entity: PIIEntity, replacement: str) -> str:
        pii_type = entity.effective_type()
        original = _clean_original(entity.raw_value)
        key = (pii_type, original)
        if key not in self._mapping:
            self._mapping[key] = replacement
            self._used_replacements.add((pii_type, replacement.casefold()))
        return self._mapping[key]

    def mapping_entries(self) -> list[MappingEntry]:
        return [
            MappingEntry(pii_type=pii_type, original=original, replacement=replacement)
            for (pii_type, original), replacement in sorted(
                self._mapping.items(), key=lambda item: (item[0][0].value, item[0][1].casefold())
            )
        ]

    def write_artifacts(self, replacement_map_path: str, audit_log_path: str, audit_entries: list[AuditEntry]) -> None:
        generated_at = datetime.now(timezone.utc).isoformat()
        _write_json(
            replacement_map_path,
            {
                "generated_at": generated_at,
                "mapping_count": len(self._mapping),
                "mappings": [
                    {
                        "pii_type": entry.pii_type.value,
                        "original": entry.original,
                        "replacement": entry.replacement,
                    }
                    for entry in self.mapping_entries()
                ],
            },
        )
        _write_json(
            audit_log_path,
            {
                "generated_at": generated_at,
                "event_count": len(audit_entries),
                "events": [
                    {
                        "entity_id": entry.entity_id,
                        "pii_type": entry.pii_type.value,
                        "original": entry.original,
                        "replacement": entry.replacement,
                        "span": {
                            "start": entry.span_start,
                            "end": entry.span_end,
                            "page": entry.page,
                            "bbox": entry.bbox,
                        },
                        "source_detector": entry.source_detector,
                        "confidence": entry.confidence,
                        "image_filename": entry.image_filename,
                    }
                    for entry in audit_entries
                ],
            },
        )

    def _unique_replacement(self, pii_type: PIIType, original: str) -> str:
        for _ in range(100):
            candidate = self._candidate(pii_type, original)
            if (pii_type, candidate.casefold()) not in self._used_replacements:
                return candidate

        suffix = hashlib.sha256(f"{pii_type.value}:{original}".encode()).hexdigest()[:8]
        return f"{self._candidate(pii_type, original)} {suffix}"

    def _candidate(self, pii_type: PIIType, original: str) -> str:
        if pii_type == PIIType.PERSON:
            return self._person_for(original)
        if pii_type == PIIType.EMAIL:
            return self._email_for(original)
        if pii_type == PIIType.PHONE:
            return self._indian_phone_for(original)
        if pii_type == PIIType.ADDRESS:
            return self._indian_faker.address().replace("\n", ", ")
        if pii_type == PIIType.COMPANY:
            return self._indian_faker.company()
        if pii_type == PIIType.SSN:
            return self._faker.ssn()
        if pii_type == PIIType.CREDIT_CARD:
            return self._faker.credit_card_number(card_type=None)
        if pii_type == PIIType.DOB:
            return self._dob_for(original)
        if pii_type == PIIType.IP_ADDRESS:
            return self._faker.ipv4_private()
        return f"REDACTED-{pii_type.value.upper()}"

    def _person_for(self, original: str) -> str:
        key = _name_key(original)
        key_tokens = set(_tokenize(key))
        for existing_key, replacement in self._person_names.items():
            if key_tokens.intersection(_tokenize(existing_key)):
                self._person_names[key] = replacement
                return replacement
        if key not in self._person_names:
            self._person_names[key] = self._person_name()
        return self._person_names[key]

    def _email_for(self, original: str) -> str:
        local_part, _, _domain = original.partition("@")
        related_name = self._related_person_for_email(local_part)
        if related_name:
            slug = _slug_name(related_name)
        else:
            related_name = self._person_name()
            local_key = _name_key(local_part)
            if local_key:
                self._person_names[local_key] = related_name
            slug = _slug_name(related_name)
        return f"{slug}@example.com"

    def _related_person_for_email(self, local_part: str) -> str | None:
        local_tokens = set(_tokenize(local_part))
        if not local_tokens:
            return None
        for original_name, replacement in self._person_names.items():
            if local_tokens.intersection(_tokenize(original_name)):
                return replacement
        return None

    def _indian_phone_for(self, original: str) -> str:
        rng = random.Random(hashlib.sha256(original.encode()).hexdigest())
        number = f"{rng.choice([6, 7, 8, 9])}{rng.randrange(10**9):09d}"
        if original.strip().startswith("+"):
            return f"+91 {number[:5]} {number[5:]}"
        return f"{number[:5]} {number[5:]}"

    def _dob_for(self, original: str) -> str:
        generated = self._faker.date_of_birth(minimum_age=18, maximum_age=90)
        return _format_like_date(original, generated)

    def _person_name(self) -> str:
        return f"{self._faker.first_name()} {self._faker.last_name()}"


def build_audit_entry(entity: PIIEntity, replacement: str, image_filename: str | None = None) -> AuditEntry:
    return AuditEntry(
        entity_id=entity.id,
        pii_type=entity.effective_type(),
        original=_clean_original(entity.raw_value),
        replacement=replacement,
        span_start=entity.span.start,
        span_end=entity.span.end,
        page=entity.span.page,
        bbox=entity.span.bbox,
        source_detector=entity.source_detector,
        confidence=entity.confidence,
        image_filename=image_filename,
    )


def _clean_original(value: str) -> str:
    return " ".join(value.split())


def _name_key(value: str) -> str:
    return " ".join(_tokenize(value))


def _tokenize(value: str) -> list[str]:
    tokens = ["".join(ch for ch in token.lower() if ch.isalnum()) for token in value.replace(".", " ").split()]
    return [token for token in tokens if token]


def _slug_name(value: str) -> str:
    tokens = [token for token in _tokenize(value) if token]
    return ".".join(tokens[:2]) if tokens else "redacted.user"


def _format_like_date(original: str, generated: date) -> str:
    stripped = original.strip()
    if "-" in stripped:
        if len(stripped.split("-")[0]) == 4:
            return generated.strftime("%Y-%m-%d")
        return generated.strftime("%m-%d-%Y")
    if "/" in stripped:
        return generated.strftime("%m/%d/%Y")
    if "," in stripped:
        return generated.strftime("%B %d, %Y")
    return generated.strftime("%B %d %Y")


def _write_json(path: str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
