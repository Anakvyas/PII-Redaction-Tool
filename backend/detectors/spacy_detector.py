"""Statistical NER for the two PII types that don't have a fixed shape:
Person and Company. Kept as an independent adapter alongside PresidioDetector
(same underlying model family, separate pipeline) so the two can corroborate
each other in DetectionPipeline — two independent detectors agreeing on a
span is a stronger signal than either alone."""
from __future__ import annotations

from detectors.base import BaseDetector
from core.exceptions import DetectorUnavailableError
from schemas.common import PIIEntity, PIIType, TextSpan
from utils.fuzzy import adjust_company_confidence
from utils.ids import new_id

_LABEL_MAP = {
    "PERSON": PIIType.PERSON,
    "ORG": PIIType.COMPANY,
}
_CONFIDENCE = {
    PIIType.PERSON: 0.85,
    PIIType.COMPANY: 0.8,
}


class SpacyNERDetector(BaseDetector):
    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        self._model_name = model_name
        self._nlp = None

    @property
    def name(self) -> str:
        return "spacy_ner_detector"

    def supports(self, pii_type: PIIType) -> bool:
        return pii_type in _CONFIDENCE

    def _load(self):
        if self._nlp is None:
            try:
                import spacy
            except ImportError as exc:
                raise DetectorUnavailableError(
                    "spaCy is not installed. Run: pip install spacy"
                ) from exc
            try:
                self._nlp = spacy.load(self._model_name)
            except OSError as exc:
                raise DetectorUnavailableError(
                    f"spaCy model '{self._model_name}' is not installed. "
                    f"Run: python -m spacy download {self._model_name}"
                ) from exc
        return self._nlp

    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        wanted_labels = {label for label, t in _LABEL_MAP.items() if t in pii_types}
        if not wanted_labels or not text.strip():
            return []

        nlp = self._load()
        doc = nlp(text)
        entities: list[PIIEntity] = []
        for ent in doc.ents:
            if ent.label_ not in wanted_labels:
                continue
            pii_type = _LABEL_MAP[ent.label_]
            confidence = _CONFIDENCE[pii_type]

            if pii_type == PIIType.COMPANY:
                confidence = adjust_company_confidence(ent.text, confidence)

            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=pii_type,
                    span=TextSpan(start=ent.start_char, end=ent.end_char),
                    raw_value=ent.text,
                    confidence=confidence,
                    source_detector=self.name,
                )
            )
        return entities
