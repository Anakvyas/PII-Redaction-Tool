"""Shared replacement planning for format-specific redactors."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import PIIEntity, PIIType, RedactionStrategy
from replacement.faker_engine import AuditEntry, FakerReplacementEngine, build_audit_entry
from replacement.strategies import resolve_replacement


@dataclass(frozen=True)
class PlannedReplacement:
    entity: PIIEntity
    replacement: str


@dataclass(frozen=True)
class ReplacementPlan:
    replacements: list[PlannedReplacement]
    counts_by_type: dict[PIIType, int]
    audit_entries: list[AuditEntry]
    faker_engine: FakerReplacementEngine


def is_word_safe_span(text: str, start: int, end: int) -> bool:
    """Return False when a detection would replace only part of a word."""
    if start < 0 or end > len(text) or start >= end:
        return False

    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return not _is_word_char(before) and not _is_word_char(after)


def plan_replacements(
    entities: list[PIIEntity],
    source_text: str,
    strategy_map: dict[PIIType, RedactionStrategy],
    *,
    black_box_as_empty: bool = False,
) -> ReplacementPlan:
    """Build non-overlapping, word-boundary-safe replacements in document order."""
    faker_engine = FakerReplacementEngine()
    counts_by_type: dict[PIIType, int] = {}
    planned: list[PlannedReplacement] = []
    audit_entries: list[AuditEntry] = []

    for entity in sorted(entities, key=lambda e: (e.span.start, -(e.span.end - e.span.start), e.id)):
        if any(entity.span.start < p.entity.span.end and p.entity.span.start < entity.span.end for p in planned):
            continue
        if not is_word_safe_span(source_text, entity.span.start, entity.span.end):
            continue

        strategy = strategy_map.get(entity.effective_type(), RedactionStrategy.MASK)
        replacement = (
            faker_engine.register_static_replacement(entity, "[BLACK-BOX]")
            if black_box_as_empty and strategy == RedactionStrategy.BLACK_BOX
            else resolve_replacement(entity, strategy, faker_engine)
        )
        document_replacement = "" if black_box_as_empty and strategy == RedactionStrategy.BLACK_BOX else replacement
        planned.append(PlannedReplacement(entity=entity, replacement=document_replacement))
        audit_entries.append(build_audit_entry(entity, replacement))

        key = entity.effective_type()
        counts_by_type[key] = counts_by_type.get(key, 0) + 1

    return ReplacementPlan(
        replacements=planned,
        counts_by_type=counts_by_type,
        audit_entries=audit_entries,
        faker_engine=faker_engine,
    )


def _is_word_char(value: str) -> bool:
    return bool(value) and (value.isalnum() or value == "_")
