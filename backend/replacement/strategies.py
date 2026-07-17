"""Per-entity text replacement strategies."""
from __future__ import annotations

from datetime import datetime

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from replacement.faker_engine import FakerReplacementEngine

_DATE_FORMATS = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y")


def mask_replacement(entity: PIIEntity) -> str:
    return f"[REDACTED-{entity.effective_type().value.upper()}]"


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
    faker_engine: FakerReplacementEngine,
) -> str:
    if strategy == RedactionStrategy.PSEUDONYMIZE:
        return faker_engine.pseudonymize(entity)
    if strategy == RedactionStrategy.GENERALIZE:
        return faker_engine.register_static_replacement(entity, generalize_replacement(entity))
    return faker_engine.register_static_replacement(
        entity, mask_replacement(entity)
    )  # MASK, and BLACK_BOX's non-visual fallback
