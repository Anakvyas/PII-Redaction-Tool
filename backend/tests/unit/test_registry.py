from detectors.regex_detector import RegexDetector
from detectors.date_detector import DateDetector
from detectors.registry import DetectorRegistry
from schemas.common import PIIType


def _registry():
    return DetectorRegistry([RegexDetector(), DateDetector()])


class TestDetectorsFor:
    def test_returns_only_supporting_detectors(self):
        registry = _registry()
        names = [d.name for d in registry.detectors_for(PIIType.SSN)]
        assert names == ["regex_detector"]

    def test_dob_only_supported_by_date_detector(self):
        registry = _registry()
        names = [d.name for d in registry.detectors_for(PIIType.DOB)]
        assert names == ["date_detector"]


class TestCatalog:
    def test_catalog_covers_every_pii_type(self):
        registry = _registry()
        catalog = registry.catalog()
        assert set(catalog.keys()) == set(PIIType)

    def test_catalog_lists_correct_detectors(self):
        registry = _registry()
        catalog = registry.catalog()
        assert catalog[PIIType.EMAIL] == ["regex_detector"]
        assert catalog[PIIType.DOB] == ["date_detector"]
        assert catalog[PIIType.PERSON] == []


class TestDetectAll:
    def test_fans_out_to_multiple_detectors(self):
        registry = _registry()
        text = "SSN 234-56-7890, DOB 03/14/1985."
        entities = registry.detect_all(text, {PIIType.SSN, PIIType.DOB})
        types_found = {e.pii_type for e in entities}
        assert types_found == {PIIType.SSN, PIIType.DOB}

    def test_only_returns_requested_types(self):
        registry = _registry()
        text = "SSN 234-56-7890, DOB 03/14/1985."
        entities = registry.detect_all(text, {PIIType.SSN})
        assert {e.pii_type for e in entities} == {PIIType.SSN}
