"""End-to-end tests for the public PII Detection Engine contract
(detectors/engine.py): Presidio + spaCy + regex + RapidFuzz fanned out,
merged, and normalized down to `[{type, text, start, end, confidence}, ...]`."""
import pytest

from detectors import engine
from schemas.common import PIIType

SAMPLE_TEXT = (
    "Employee Onboarding Form\n\n"
    "Jane Doe works at Globex Corporation and can be reached at "
    "jane.doe@example.com or 555-123-4567. Her SSN on file is 234-56-7890 "
    "and her date of birth is 03/14/1985. The company card charged was "
    "4539148803436467, and her last login came from IP 192.168.1.15. "
    "Her mailing address is 742 Evergreen Terrace, Springfield, IL 62704.\n"
)

REQUIRED_KEYS = {"type", "text", "start", "end", "confidence"}


@pytest.fixture(scope="module", autouse=True)
def _use_shared_pipeline(detection_pipeline):
    # Reuse the session-scoped models from conftest instead of letting
    # engine.py's own container singleton load en_core_web_lg a second time.
    # Module-scoped (not pytest's function-scoped `monkeypatch`) so it stays
    # applied for every test in this file, including the module-scoped
    # `all_detections` fixture below.
    original = engine.get_detection_pipeline
    engine.get_detection_pipeline = lambda: detection_pipeline
    yield
    engine.get_detection_pipeline = original


@pytest.fixture(scope="module")
def all_detections():
    return engine.detect_pii(SAMPLE_TEXT)


class TestReturnContract:
    def test_returns_list_of_dicts_with_exact_keys(self, all_detections):
        assert isinstance(all_detections, list)
        assert all_detections, "expected at least one detection in the sample text"
        for item in all_detections:
            assert set(item.keys()) == REQUIRED_KEYS

    def test_confidence_is_a_float_between_zero_and_one(self, all_detections):
        for item in all_detections:
            assert isinstance(item["confidence"], float)
            assert 0.0 <= item["confidence"] <= 1.0

    def test_span_matches_text_exactly(self, all_detections):
        for item in all_detections:
            assert SAMPLE_TEXT[item["start"] : item["end"]] == item["text"]

    def test_results_are_ordered_left_to_right(self, all_detections):
        starts = [item["start"] for item in all_detections]
        assert starts == sorted(starts)


class TestOverlapResolution:
    def test_no_two_detections_overlap(self, all_detections):
        ordered = sorted(all_detections, key=lambda d: d["start"])
        for previous, current in zip(ordered, ordered[1:]):
            assert previous["end"] <= current["start"]


class TestCoverageAcrossAllNineTypes:
    @pytest.mark.parametrize(
        "pii_type,expected_text",
        [
            (PIIType.PERSON, "Jane Doe"),
            (PIIType.COMPANY, "Globex Corporation"),
            (PIIType.EMAIL, "jane.doe@example.com"),
            (PIIType.PHONE, "555-123-4567"),
            (PIIType.SSN, "234-56-7890"),
            (PIIType.CREDIT_CARD, "4539148803436467"),
            (PIIType.IP_ADDRESS, "192.168.1.15"),
            (PIIType.DOB, "03/14/1985"),
        ],
    )
    def test_type_detected_with_correct_text(self, all_detections, pii_type, expected_text):
        matches = [d for d in all_detections if d["type"] == pii_type.value]
        assert matches, f"no {pii_type.value} detection found"
        assert any(m["text"] == expected_text for m in matches)

    def test_address_detected(self, all_detections):
        matches = [d for d in all_detections if d["type"] == PIIType.ADDRESS.value]
        assert matches
        assert matches[0]["text"].startswith("742 Evergreen Terrace")


class TestTypeFiltering:
    def test_restricting_to_one_type_returns_only_that_type(self):
        results = engine.detect_pii(SAMPLE_TEXT, pii_types={PIIType.EMAIL})
        assert results
        assert all(r["type"] == PIIType.EMAIL.value for r in results)


class TestEmptyInput:
    def test_empty_text_returns_empty_list(self):
        assert engine.detect_pii("") == []
