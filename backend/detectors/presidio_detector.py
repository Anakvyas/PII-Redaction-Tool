"""Microsoft Presidio adapter, backed by spaCy's large English model. Presidio
brings its own well-tested recognizers for the format-anchored types (email,
phone via `phonenumbers`, credit card, SSN, IP) plus spaCy-NER-derived PERSON/
ORGANIZATION/LOCATION/DATE_TIME — this is the primary statistical source, with
RegexDetector and SpacyNERDetector left in the registry as independent,
corroborating signals (see DetectionPipeline._boost_corroborated)."""
from __future__ import annotations

from detectors.base import BaseDetector
from core.exceptions import DetectorUnavailableError
from schemas.common import PIIEntity, PIIType, TextSpan
from utils.fuzzy import DOB_CONTEXT_KEYWORDS, adjust_company_confidence, fuzzy_contains_keyword
from utils.ids import new_id
from utils.text import context_window, preceding_word

_ENTITY_MAP: dict[str, PIIType] = {
    "PERSON": PIIType.PERSON,
    "ORGANIZATION": PIIType.COMPANY,
    "EMAIL_ADDRESS": PIIType.EMAIL,
    "PHONE_NUMBER": PIIType.PHONE,
    "CREDIT_CARD": PIIType.CREDIT_CARD,
    "US_SSN": PIIType.SSN,
    "IP_ADDRESS": PIIType.IP_ADDRESS,
    "LOCATION": PIIType.ADDRESS,
    "DATE_TIME": PIIType.DOB,
}


class PresidioDetector(BaseDetector):
    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        self._model_name = model_name
        self._analyzer = None

    @property
    def name(self) -> str:
        return "presidio_detector"

    def supports(self, pii_type: PIIType) -> bool:
        return pii_type in _ENTITY_MAP.values()

    def _load(self):
        if self._analyzer is not None:
            return self._analyzer
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
        except ImportError as exc:
            raise DetectorUnavailableError(
                "presidio-analyzer is not installed. Run: pip install presidio-analyzer"
            ) from exc

        try:
            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": self._model_name}],
                }
            )
            nlp_engine = provider.create_engine()
        except OSError as exc:
            raise DetectorUnavailableError(
                f"spaCy model '{self._model_name}' is not installed. "
                f"Run: python -m spacy download {self._model_name}"
            ) from exc

        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        return self._analyzer

    def detect(self, text: str, pii_types: set[PIIType]) -> list[PIIEntity]:
        wanted_labels = [label for label, t in _ENTITY_MAP.items() if t in pii_types]
        if not wanted_labels or not text.strip():
            return []

        analyzer = self._load()
        results = analyzer.analyze(text=text, language="en", entities=wanted_labels)

        entities: list[PIIEntity] = []
        for result in results:
            pii_type = _ENTITY_MAP[result.entity_type]
            confidence = float(result.score)
            raw_value = text[result.start : result.end]

            if pii_type == PIIType.DOB:
                # DATE_TIME fires on every date in the document (invoice
                # dates, meeting dates, ...) — only trust it as a DOB
                # candidate near explicit birth-context language.
                window = context_window(text, result.start, result.end)
                if not fuzzy_contains_keyword(window, DOB_CONTEXT_KEYWORDS):
                    continue
                confidence = max(confidence, 0.75)

            if pii_type == PIIType.COMPANY:
                confidence = adjust_company_confidence(raw_value, confidence, preceding_word(text, result.start))

            if pii_type == PIIType.ADDRESS:
                # LOCATION alone is usually just a city/country/landmark
                # name, not a full street address — cap it below the regex
                # street-address detector so the more specific match wins
                # any overlap, while still surfacing as a low-confidence
                # candidate when regex finds nothing.
                confidence = min(confidence, 0.6)

            entities.append(
                PIIEntity(
                    id=new_id("det"),
                    pii_type=pii_type,
                    span=TextSpan(start=result.start, end=result.end),
                    raw_value=raw_value,
                    confidence=confidence,
                    source_detector=self.name,
                )
            )
        return entities
