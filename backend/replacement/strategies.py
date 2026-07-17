"""Per-entity text replacement strategies. `black_box` is PDF-only and is
handled directly by replacement/pdf_redactor.py (it draws glyph-removing
annotations rather than substituting text), so it isn't a text strategy here —
callers fall back to the mask token for it in non-visual contexts (DOCX)."""
from __future__ import annotations

from datetime import datetime

from schemas.common import PIIEntity, PIIType, RedactionStrategy

_PSEUDONYM_TEMPLATES: dict[PIIType, str] = {
    PIIType.PERSON: "Person {n}",
    PIIType.EMAIL: "user{n}@example.com",
    PIIType.PHONE: "555-01{n:02d}-0000",
    PIIType.COMPANY: "Company {n}",
    PIIType.ADDRESS: "{n} Example St, Springfield",
    PIIType.SSN: "000-00-{n:04d}",
    PIIType.CREDIT_CARD: "4111-1111-1111-{n:04d}",
    PIIType.DOB: "01/01/1970",
    PIIType.IP_ADDRESS: "10.0.0.{n}",
}

_DATE_FORMATS = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y")


def mask_replacement(entity: PIIEntity) -> str:
    return f"[REDACTED-{entity.effective_type().value.upper()}]"


def pseudonymize_replacement(
    entity: PIIEntity, consistency_map: dict[str, str], counters: dict[PIIType, int]
) -> str:
    """Same source value always maps to the same fake value within a job."""
    if entity.raw_value in consistency_map:
        return consistency_map[entity.raw_value]
    pii_type = entity.effective_type()
    counters[pii_type] = counters.get(pii_type, 0) + 1
    template = _PSEUDONYM_TEMPLATES.get(pii_type, "REDACTED-{n}")
    value = template.format(n=counters[pii_type])
    consistency_map[entity.raw_value] = value
    return value


def _try_parse_date(raw: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _age_from(dob: datetime) -> int:
    today = datetime.now()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(age, 0)


def generalize_replacement(entity: PIIEntity) -> str:
    """Reduce precision instead of removing outright."""
    pii_type = entity.effective_type()
    if pii_type == PIIType.DOB:
        parsed = _try_parse_date(entity.raw_value)
        if parsed:
            lower = (_age_from(parsed) // 10) * 10
            return f"[AGE {lower}-{lower + 9}]"
        return "[REDACTED-DOB]"
    if pii_type == PIIType.ADDRESS:
        parts = [p.strip() for p in entity.raw_value.split(",")]
        if len(parts) >= 2:
            return f"[REDACTED STREET], {', '.join(parts[1:])}"
        return "[REDACTED-ADDRESS]"
    if pii_type == PIIType.PHONE:
        digits = "".join(c for c in entity.raw_value if c.isdigit())
        return f"[PHONE ENDING {digits[-4:]}]" if len(digits) >= 4 else "[REDACTED-PHONE]"
    if pii_type == PIIType.IP_ADDRESS and "." in entity.raw_value:
        octets = entity.raw_value.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.x.x"
    return mask_replacement(entity)


def resolve_replacement(
    entity: PIIEntity,
    strategy: RedactionStrategy,
    consistency_map: dict[str, str],
    counters: dict[PIIType, int],
) -> str:
    if strategy == RedactionStrategy.PSEUDONYMIZE:
        return pseudonymize_replacement(entity, consistency_map, counters)
    if strategy == RedactionStrategy.GENERALIZE:
        return generalize_replacement(entity)
    return mask_replacement(entity)  # MASK, and BLACK_BOX's non-visual fallback
