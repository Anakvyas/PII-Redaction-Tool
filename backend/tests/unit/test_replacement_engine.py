from __future__ import annotations

from schemas.common import PIIEntity, PIIType, RedactionStrategy, TextSpan
from replacement.engine import is_word_safe_span, plan_replacements


def _entity(
    entity_id: str,
    start: int,
    end: int,
    raw_value: str,
    pii_type: PIIType = PIIType.PERSON,
) -> PIIEntity:
    return PIIEntity(
        id=entity_id,
        pii_type=pii_type,
        span=TextSpan(start=start, end=end),
        raw_value=raw_value,
        confidence=0.99,
        source_detector="test",
    )


def test_word_safe_span_rejects_partial_words() -> None:
    text = "Ann met Annual Report."

    assert is_word_safe_span(text, 0, 3)
    assert not is_word_safe_span(text, 8, 11)


def test_plan_replacements_keeps_multiple_whole_word_occurrences() -> None:
    text = "Ann called Ann."
    first = text.index("Ann")
    second = text.rindex("Ann")

    plan = plan_replacements(
        [_entity("e1", first, first + 3, "Ann"), _entity("e2", second, second + 3, "Ann")],
        text,
        {PIIType.PERSON: RedactionStrategy.MASK},
    )

    assert [p.entity.id for p in plan.replacements] == ["e1", "e2"]
    assert [p.replacement for p in plan.replacements] == ["[REDACTED-PERSON]", "[REDACTED-PERSON]"]
    assert plan.counts_by_type == {PIIType.PERSON: 2}


def test_plan_replacements_drops_overlapping_lower_priority_span() -> None:
    text = "Jane Doe"

    plan = plan_replacements(
        [_entity("long", 0, 8, "Jane Doe"), _entity("short", 0, 4, "Jane")],
        text,
        {PIIType.PERSON: RedactionStrategy.MASK},
    )

    assert [p.entity.id for p in plan.replacements] == ["long"]
    assert plan.counts_by_type == {PIIType.PERSON: 1}


def test_pseudonymize_reuses_person_mapping_for_every_occurrence() -> None:
    text = "John Smith met John Smith."
    first = text.index("John Smith")
    second = text.rindex("John Smith")

    plan = plan_replacements(
        [
            _entity("e1", first, first + 10, "John Smith"),
            _entity("e2", second, second + 10, "John Smith"),
        ],
        text,
        {PIIType.PERSON: RedactionStrategy.PSEUDONYMIZE},
    )

    assert len(plan.replacements) == 2
    assert plan.replacements[0].replacement == plan.replacements[1].replacement
    assert plan.replacements[0].replacement != "John Smith"
    assert len(plan.faker_engine.mapping_entries()) == 1


def test_pseudonymize_generates_matching_email_from_person_mapping() -> None:
    text = "John Smith uses john@gmail.com."
    name_start = text.index("John Smith")
    email_start = text.index("john@gmail.com")

    plan = plan_replacements(
        [
            _entity("person", name_start, name_start + 10, "John Smith"),
            _entity("email", email_start, email_start + 14, "john@gmail.com", PIIType.EMAIL),
        ],
        text,
        {
            PIIType.PERSON: RedactionStrategy.PSEUDONYMIZE,
            PIIType.EMAIL: RedactionStrategy.PSEUDONYMIZE,
        },
    )

    replacements = {p.entity.id: p.replacement for p in plan.replacements}
    expected_slug = ".".join(replacements["person"].lower().split()[:2])
    assert replacements["email"] == f"{expected_slug}@example.com"
