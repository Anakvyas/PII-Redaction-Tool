"""Exercises Presidio's AnalyzerEngine (spaCy en_core_web_lg NlpEngine plus
Presidio's built-in recognizers) via the session-scoped fixture."""
from schemas.common import PIIType


class TestSupports:
    def test_supports_all_nine_types(self, presidio_detector):
        for pii_type in PIIType:
            assert presidio_detector.supports(pii_type) is True


class TestStructuredRecognizers:
    def test_detects_email(self, presidio_detector):
        entities = presidio_detector.detect("Reach jane.doe@example.com", {PIIType.EMAIL})
        assert any(e.raw_value == "jane.doe@example.com" for e in entities)

    def test_detects_ssn(self, presidio_detector):
        entities = presidio_detector.detect("SSN 234-56-7890 on file", {PIIType.SSN})
        assert any(e.pii_type == PIIType.SSN for e in entities)

    def test_detects_credit_card(self, presidio_detector):
        entities = presidio_detector.detect("Card 4539148803436467 charged", {PIIType.CREDIT_CARD})
        assert any(e.pii_type == PIIType.CREDIT_CARD for e in entities)

    def test_detects_ip_address(self, presidio_detector):
        entities = presidio_detector.detect("Login from 192.168.1.15", {PIIType.IP_ADDRESS})
        assert any(e.raw_value == "192.168.1.15" for e in entities)


class TestPersonRecognizer:
    def test_detects_person_name(self, presidio_detector):
        entities = presidio_detector.detect("John Smith signed the form.", {PIIType.PERSON})
        assert any(e.pii_type == PIIType.PERSON for e in entities)


class TestDobContextGate:
    def test_date_with_birth_context_is_kept(self, presidio_detector):
        entities = presidio_detector.detect("Date of birth: March 14, 1985.", {PIIType.DOB})
        assert any(e.pii_type == PIIType.DOB for e in entities)

    def test_date_without_birth_context_is_dropped(self, presidio_detector):
        entities = presidio_detector.detect("Invoice dated March 14, 1985.", {PIIType.DOB})
        assert entities == []


class TestSpanIntegrity:
    def test_span_matches_raw_value_in_source_text(self, presidio_detector):
        text = "Contact jane.doe@example.com or SSN 234-56-7890."
        entities = presidio_detector.detect(text, {PIIType.EMAIL, PIIType.SSN})
        for entity in entities:
            assert text[entity.span.start : entity.span.end] == entity.raw_value
