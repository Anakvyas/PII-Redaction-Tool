"""Composition root for stateless singletons. Request-scoped services (those
needing a DB session) are constructed per-request in api/v1/deps.py instead —
this module only holds things that are safe and desirable to build once."""
from __future__ import annotations

from functools import lru_cache

from config.settings import get_settings
from detectors.date_detector import DateDetector
from detectors.labeled_field_detector import LabeledFieldDetector
from detectors.presidio_detector import PresidioDetector
from detectors.regex_detector import RegexDetector
from detectors.registry import DetectorRegistry
from detectors.spacy_detector import SpacyNERDetector
from services.detection_service import DetectionPipeline
from services.storage_service import FileStorage, build_storage


@lru_cache
def get_detector_registry() -> DetectorRegistry:
    settings = get_settings()
    spacy_detector = SpacyNERDetector(model_name=settings.SPACY_MODEL)
    return DetectorRegistry(
        [
            RegexDetector(),
            DateDetector(),
            spacy_detector,
            # Reuses spacy_detector's pipeline once loaded, instead of loading
            # a second full copy of the same model (see PresidioDetector._load).
            PresidioDetector(model_name=settings.SPACY_MODEL, spacy_ner_detector=spacy_detector),
            LabeledFieldDetector(),
        ]
    )


@lru_cache
def get_detection_pipeline() -> DetectionPipeline:
    return DetectionPipeline(get_detector_registry())


@lru_cache
def get_storage() -> FileStorage:
    return build_storage(get_settings())
