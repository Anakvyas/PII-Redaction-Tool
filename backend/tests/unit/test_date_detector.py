from datetime import datetime

from schemas.common import PIIType


class TestSupports:
    def test_supports_dob_only(self, date_detector):
        assert date_detector.supports(PIIType.DOB) is True
        assert date_detector.supports(PIIType.PERSON) is False


class TestContextConfidence:
    def test_high_confidence_with_birth_context(self, date_detector):
        entities = date_detector.detect("Patient DOB: 03/14/1985.", {PIIType.DOB})
        assert len(entities) == 1
        assert entities[0].raw_value == "03/14/1985"
        assert entities[0].confidence >= 0.9

    def test_low_confidence_without_birth_context(self, date_detector):
        entities = date_detector.detect("Invoice due 03/14/1985.", {PIIType.DOB})
        assert len(entities) == 1
        assert entities[0].confidence < 0.5

    def test_month_name_format_with_context(self, date_detector):
        entities = date_detector.detect("Born on January 5, 1990 in Ohio.", {PIIType.DOB})
        assert len(entities) == 1
        assert entities[0].raw_value == "January 5, 1990"
        assert entities[0].confidence >= 0.9

    def test_iso_format_with_context(self, date_detector):
        entities = date_detector.detect("date of birth: 1985-03-14", {PIIType.DOB})
        assert len(entities) == 1
        assert entities[0].raw_value == "1985-03-14"


class TestImplausibleDates:
    def test_future_year_not_detected(self, date_detector):
        future_year = datetime.now().year + 5
        entities = date_detector.detect(f"Expires 01/01/{future_year}.", {PIIType.DOB})
        assert entities == []

    def test_year_older_than_120_not_detected(self, date_detector):
        entities = date_detector.detect("Founded 01/01/1850.", {PIIType.DOB})
        assert entities == []


class TestRequestScoping:
    def test_returns_nothing_when_dob_not_requested(self, date_detector):
        entities = date_detector.detect("DOB: 03/14/1985.", {PIIType.SSN})
        assert entities == []


class TestSpanIntegrity:
    def test_span_matches_raw_value_in_source_text(self, date_detector):
        text = "Patient date of birth: 03/14/1985 confirmed."
        entities = date_detector.detect(text, {PIIType.DOB})
        for entity in entities:
            assert text[entity.span.start : entity.span.end] == entity.raw_value
