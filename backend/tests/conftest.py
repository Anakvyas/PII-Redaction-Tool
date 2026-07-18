"""Session-scoped fixtures for the NLP-backed detectors. Loading
en_core_web_md is the expensive part of this test suite; presidio_detector
reuses spacy_detector's already-loaded pipeline (mirroring container.py's
wiring) so it's loaded exactly once per test run, not twice."""
from __future__ import annotations

import pytest

from detectors.date_detector import DateDetector
from detectors.labeled_field_detector import LabeledFieldDetector
from detectors.presidio_detector import PresidioDetector
from detectors.regex_detector import RegexDetector
from detectors.registry import DetectorRegistry
from detectors.spacy_detector import SpacyNERDetector
from services.detection_service import DetectionPipeline


@pytest.fixture(scope="session")
def regex_detector() -> RegexDetector:
    return RegexDetector()


@pytest.fixture(scope="session")
def date_detector() -> DateDetector:
    return DateDetector()


@pytest.fixture(scope="session")
def spacy_detector() -> SpacyNERDetector:
    return SpacyNERDetector()


@pytest.fixture(scope="session")
def presidio_detector(spacy_detector: SpacyNERDetector) -> PresidioDetector:
    return PresidioDetector(spacy_ner_detector=spacy_detector)


@pytest.fixture(scope="session")
def labeled_field_detector() -> LabeledFieldDetector:
    return LabeledFieldDetector()


@pytest.fixture(scope="session")
def detector_registry(
    regex_detector, date_detector, spacy_detector, presidio_detector, labeled_field_detector
) -> DetectorRegistry:
    return DetectorRegistry(
        [regex_detector, date_detector, spacy_detector, presidio_detector, labeled_field_detector]
    )


@pytest.fixture(scope="session")
def detection_pipeline(detector_registry) -> DetectionPipeline:
    return DetectionPipeline(detector_registry)
