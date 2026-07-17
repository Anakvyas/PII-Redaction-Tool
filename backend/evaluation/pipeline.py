"""Runs detection against the gold-standard dataset and scores it — the CI
regression gate described in the architecture (a drop below F1 threshold for
any PII type should block a detector change) is meant to call `run()` here."""
from __future__ import annotations

from core.container import get_detector_registry
from evaluation.metrics import Metrics, metrics_from_counts
from evaluation.sample_dataset import SAMPLE_DATASET, EvaluationCase
from schemas.common import DocumentFormat, ExtractedDocument, PIIType, TextBlock, TextSpan
from services.detection_service import DetectionPipeline

DETECTOR_VERSION = "v1"


class EvaluationPipeline:
    def __init__(self) -> None:
        self._detection_pipeline = DetectionPipeline(get_detector_registry())

    def run(
        self, dataset: list[EvaluationCase] | None = None
    ) -> tuple[Metrics, dict[PIIType, Metrics]]:
        cases = dataset if dataset is not None else SAMPLE_DATASET
        totals: dict[PIIType, dict[str, int]] = {t: {"tp": 0, "fp": 0, "fn": 0} for t in PIIType}

        for case in cases:
            document = ExtractedDocument(
                document_id="eval",
                format=DocumentFormat.DOCX,
                blocks=[TextBlock(text=case.text, char_offset=0)],
            )
            entities = self._detection_pipeline.run(document, set(PIIType))

            predicted_by_type: dict[PIIType, list[TextSpan]] = {}
            for entity in entities:
                predicted_by_type.setdefault(entity.pii_type, []).append(entity.span)

            expected_by_type: dict[PIIType, list[TextSpan]] = {}
            for pii_type, span in case.expected:
                expected_by_type.setdefault(pii_type, []).append(span)

            for pii_type in PIIType:
                tp, fp, fn = _match(predicted_by_type.get(pii_type, []), expected_by_type.get(pii_type, []))
                totals[pii_type]["tp"] += tp
                totals[pii_type]["fp"] += fp
                totals[pii_type]["fn"] += fn

        per_type: dict[PIIType, Metrics] = {}
        agg_tp = agg_fp = agg_fn = 0
        for pii_type, counts in totals.items():
            per_type[pii_type] = metrics_from_counts(counts["tp"], counts["fp"], counts["fn"])
            agg_tp += counts["tp"]
            agg_fp += counts["fp"]
            agg_fn += counts["fn"]

        overall = metrics_from_counts(agg_tp, agg_fp, agg_fn)
        return overall, per_type


def _match(predicted: list[TextSpan], expected: list[TextSpan]) -> tuple[int, int, int]:
    matched: set[int] = set()
    tp = 0
    for p in predicted:
        for i, e in enumerate(expected):
            if i in matched:
                continue
            if p.start < e.end and e.start < p.end:
                matched.add(i)
                tp += 1
                break
    return tp, len(predicted) - tp, len(expected) - len(matched)
