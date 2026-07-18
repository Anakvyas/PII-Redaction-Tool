"""Exercises the real en_core_web_md model via the session-scoped fixture in
conftest.py — slower than the regex/date tests, but this is the only way to
pin down actual NER behavior (including its known false-positive shape)."""
from schemas.common import PIIType


class TestSupports:
    def test_supports_person_and_company_only(self, spacy_detector):
        assert spacy_detector.supports(PIIType.PERSON) is True
        assert spacy_detector.supports(PIIType.COMPANY) is True
        assert spacy_detector.supports(PIIType.SSN) is False


class TestPersonDetection:
    def test_detects_full_name(self, spacy_detector):
        entities = spacy_detector.detect("Jane Doe joined the meeting.", {PIIType.PERSON})
        values = [e.raw_value for e in entities if e.pii_type == PIIType.PERSON]
        assert "Jane Doe" in values


class TestCompanyDetection:
    def test_known_suffix_boosts_confidence_above_base(self, spacy_detector):
        entities = spacy_detector.detect("She works at Umbrella Corporation.", {PIIType.COMPANY})
        companies = [e for e in entities if e.pii_type == PIIType.COMPANY]
        assert companies
        assert companies[0].confidence > 0.8  # base confidence is 0.8; suffix should boost it

    def test_short_acronym_confidence_is_discounted(self, spacy_detector):
        entities = spacy_detector.detect("Field: SSN", {PIIType.COMPANY})
        acronym_hits = [e for e in entities if e.pii_type == PIIType.COMPANY and e.raw_value.strip() == "SSN"]
        # If spaCy tags the bare acronym as an ORG at all, the false-positive
        # guard must have discounted it well below the base 0.8 confidence.
        for hit in acronym_hits:
            assert hit.confidence < 0.5


class TestSpanIntegrity:
    def test_span_matches_raw_value_in_source_text(self, spacy_detector):
        text = "Jane Doe works at Umbrella Corporation."
        entities = spacy_detector.detect(text, {PIIType.PERSON, PIIType.COMPANY})
        for entity in entities:
            assert text[entity.span.start : entity.span.end] == entity.raw_value
