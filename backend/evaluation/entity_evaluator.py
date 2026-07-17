"""File-based entity evaluation and report generation.

Ground truth and prediction files can be either:

1. A JSON object with an ``entities`` list.
2. A bare JSON list of entities.

Each entity accepts ``pii_type``, ``entity_type``, ``type``, or ``label`` plus
either top-level ``start``/``end`` fields or a nested ``span`` object.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from schemas.common import PIIType

NONE_LABEL = "__none__"


@dataclass(frozen=True)
class EvaluationEntity:
    pii_type: PIIType
    start: int
    end: int
    document_id: str = "default"
    text: str | None = None
    entity_id: str | None = None

    def overlaps(self, other: "EvaluationEntity") -> bool:
        return self.document_id == other.document_id and self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class EntityMatch:
    ground_truth: EvaluationEntity | None
    prediction: EvaluationEntity | None
    outcome: str


@dataclass(frozen=True)
class CountMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    entity_accuracy: float
    support: int


@dataclass(frozen=True)
class EvaluationReport:
    overall: CountMetrics
    per_type: dict[PIIType, CountMetrics]
    confusion_matrix: dict[str, dict[str, int]]
    classification_report: dict[str, CountMetrics]
    matches: list[EntityMatch]


def evaluate_entities(
    ground_truth: list[EvaluationEntity],
    predictions: list[EvaluationEntity],
) -> EvaluationReport:
    matches = match_entities(ground_truth, predictions)
    labels = sorted({entity.pii_type for entity in ground_truth + predictions}, key=lambda item: item.value)

    per_type: dict[PIIType, CountMetrics] = {}
    for pii_type in labels:
        tp = sum(1 for match in matches if _is_tp_for(match, pii_type))
        fp = sum(1 for match in matches if _is_fp_for(match, pii_type))
        fn = sum(1 for match in matches if _is_fn_for(match, pii_type))
        per_type[pii_type] = metrics_from_counts(tp, fp, fn)

    total_tp = sum(metric.true_positives for metric in per_type.values())
    total_fp = sum(metric.false_positives for metric in per_type.values())
    total_fn = sum(metric.false_negatives for metric in per_type.values())
    overall = metrics_from_counts(total_tp, total_fp, total_fn)
    confusion = build_confusion_matrix(matches, labels)

    return EvaluationReport(
        overall=overall,
        per_type=per_type,
        confusion_matrix=confusion,
        classification_report={pii_type.value: metric for pii_type, metric in per_type.items()},
        matches=matches,
    )


def match_entities(
    ground_truth: list[EvaluationEntity],
    predictions: list[EvaluationEntity],
) -> list[EntityMatch]:
    """Greedily match predictions to overlapping ground-truth entities."""
    matches: list[EntityMatch] = []
    matched_gt: set[int] = set()
    matched_pred: set[int] = set()

    for pred_index, prediction in enumerate(predictions):
        best_index = _best_overlap_index(prediction, ground_truth, matched_gt)
        if best_index is None:
            continue

        matched_gt.add(best_index)
        matched_pred.add(pred_index)
        expected = ground_truth[best_index]
        outcome = "true_positive" if expected.pii_type == prediction.pii_type else "type_mismatch"
        matches.append(EntityMatch(ground_truth=expected, prediction=prediction, outcome=outcome))

    for pred_index, prediction in enumerate(predictions):
        if pred_index not in matched_pred:
            matches.append(EntityMatch(ground_truth=None, prediction=prediction, outcome="false_positive"))

    for gt_index, expected in enumerate(ground_truth):
        if gt_index not in matched_gt:
            matches.append(EntityMatch(ground_truth=expected, prediction=None, outcome="false_negative"))

    return matches


def metrics_from_counts(tp: int, fp: int, fn: int) -> CountMetrics:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    entity_accuracy = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
    return CountMetrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        entity_accuracy=entity_accuracy,
        support=tp + fn,
    )


def build_confusion_matrix(
    matches: list[EntityMatch],
    labels: list[PIIType],
) -> dict[str, dict[str, int]]:
    label_values = [label.value for label in labels]
    columns = [*label_values, NONE_LABEL]
    matrix = {row: {column: 0 for column in columns} for row in [*label_values, NONE_LABEL]}

    for match in matches:
        actual = match.ground_truth.pii_type.value if match.ground_truth else NONE_LABEL
        predicted = match.prediction.pii_type.value if match.prediction else NONE_LABEL
        matrix[actual][predicted] += 1

    return matrix


def load_entities(path: str) -> list[EvaluationEntity]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_entities = payload.get("entities", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_entities, list):
        raise ValueError("Entity JSON must be a list or an object with an 'entities' list.")
    return [_parse_entity(item, index) for index, item in enumerate(raw_entities)]


def generate_annotation_template(prediction_path: str | None, output_path: str) -> None:
    entities = load_entities(prediction_path) if prediction_path else []
    payload = {
        "schema_version": "1.0",
        "instructions": "Review each entity, correct pii_type/start/end/text, delete false positives, and add missed entities.",
        "entities": [
            {
                "id": entity.entity_id or f"annotation-{index + 1}",
                "document_id": entity.document_id,
                "pii_type": entity.pii_type.value,
                "start": entity.start,
                "end": entity.end,
                "text": entity.text,
                "annotator_decision": "accept",
            }
            for index, entity in enumerate(entities)
        ],
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_reports(report: EvaluationReport, output_dir: str, prefix: str = "evaluation") -> dict[str, str]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": str(directory / f"{prefix}_report.json"),
        "csv": str(directory / f"{prefix}_report.csv"),
        "markdown": str(directory / f"{prefix}_report.md"),
        "pdf": str(directory / f"{prefix}_report.pdf"),
    }
    write_json_report(report, paths["json"])
    write_csv_report(report, paths["csv"])
    write_markdown_report(report, paths["markdown"])
    write_pdf_report(report, paths["pdf"])
    return paths


def write_json_report(report: EvaluationReport, path: str) -> None:
    payload = {
        "overall": asdict(report.overall),
        "per_type": {pii_type.value: asdict(metrics) for pii_type, metrics in report.per_type.items()},
        "confusion_matrix": report.confusion_matrix,
        "classification_report": {
            label: asdict(metrics) for label, metrics in report.classification_report.items()
        },
        "matches": [_match_to_dict(match) for match in report.matches],
        "formulas": formulas(),
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv_report(report: EvaluationReport, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "label",
                "true_positives",
                "false_positives",
                "false_negatives",
                "precision",
                "recall",
                "f1",
                "entity_accuracy",
                "support",
            ],
        )
        writer.writeheader()
        writer.writerow({"label": "overall", **asdict(report.overall)})
        for label, metrics in sorted(report.per_type.items(), key=lambda item: item[0].value):
            writer.writerow({"label": label.value, **asdict(metrics)})


def write_markdown_report(report: EvaluationReport, path: str) -> None:
    lines = [
        "# Evaluation Report",
        "",
        "## Overall",
        "",
        _metrics_table([("overall", report.overall)]),
        "",
        "## Classification Report",
        "",
        _metrics_table((label.value, metrics) for label, metrics in sorted(report.per_type.items(), key=lambda item: item[0].value)),
        "",
        "## Confusion Matrix",
        "",
        _confusion_table(report.confusion_matrix),
        "",
        "## Formulas",
        "",
        *[f"- **{name}**: `{formula}`" for name, formula in formulas().items()],
        "",
    ]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_pdf_report(report: EvaluationReport, path: str) -> None:
    text = Path(path).with_suffix(".md")
    if text.exists():
        content = text.read_text(encoding="utf-8")
    else:
        content = _plain_report_text(report)

    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        rect = fitz.Rect(36, 36, 559, 806)
        page.insert_textbox(rect, content, fontsize=9, fontname="helv")
        doc.save(path)
        doc.close()
    except Exception:
        _write_minimal_pdf(path, content)


def formulas() -> dict[str, str]:
    return {
        "true_positive": "Predicted entity overlaps an unmatched ground-truth entity with the same type.",
        "false_positive": "Predicted entity has no overlapping ground truth, or overlaps a different type.",
        "false_negative": "Ground-truth entity has no overlapping prediction with the same type.",
        "precision": "TP / (TP + FP)",
        "recall": "TP / (TP + FN)",
        "f1": "2 * Precision * Recall / (Precision + Recall)",
        "entity_accuracy": "TP / (TP + FP + FN)",
    }


def _parse_entity(raw: Any, index: int) -> EvaluationEntity:
    if not isinstance(raw, dict):
        raise ValueError(f"Entity at index {index} must be an object.")
    span = raw.get("span") if isinstance(raw.get("span"), dict) else raw
    type_value = raw.get("pii_type") or raw.get("entity_type") or raw.get("type") or raw.get("label")
    if type_value is None:
        raise ValueError(f"Entity at index {index} is missing a PII type.")
    try:
        pii_type = PIIType(str(type_value))
    except ValueError as exc:
        raise ValueError(f"Entity at index {index} has unsupported PII type '{type_value}'.") from exc

    return EvaluationEntity(
        pii_type=pii_type,
        start=int(span["start"]),
        end=int(span["end"]),
        document_id=str(raw.get("document_id") or raw.get("doc_id") or "default"),
        text=raw.get("text") or raw.get("raw_value"),
        entity_id=raw.get("id"),
    )


def _best_overlap_index(
    prediction: EvaluationEntity,
    ground_truth: list[EvaluationEntity],
    matched_gt: set[int],
) -> int | None:
    best_index: int | None = None
    best_overlap = 0
    for index, expected in enumerate(ground_truth):
        if index in matched_gt or not prediction.overlaps(expected):
            continue
        overlap = min(prediction.end, expected.end) - max(prediction.start, expected.start)
        if overlap > best_overlap:
            best_index = index
            best_overlap = overlap
    return best_index


def _is_tp_for(match: EntityMatch, pii_type: PIIType) -> bool:
    return (
        match.ground_truth is not None
        and match.prediction is not None
        and match.ground_truth.pii_type == pii_type
        and match.prediction.pii_type == pii_type
    )


def _is_fp_for(match: EntityMatch, pii_type: PIIType) -> bool:
    return match.prediction is not None and match.prediction.pii_type == pii_type and not _is_tp_for(match, pii_type)


def _is_fn_for(match: EntityMatch, pii_type: PIIType) -> bool:
    return match.ground_truth is not None and match.ground_truth.pii_type == pii_type and not _is_tp_for(match, pii_type)


def _match_to_dict(match: EntityMatch) -> dict[str, Any]:
    return {
        "outcome": match.outcome,
        "ground_truth": asdict(match.ground_truth) if match.ground_truth else None,
        "prediction": asdict(match.prediction) if match.prediction else None,
    }


def _metrics_table(rows: Any) -> str:
    lines = [
        "| Label | TP | FP | FN | Precision | Recall | F1 | Entity Accuracy | Support |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, metrics in rows:
        lines.append(
            f"| {label} | {metrics.true_positives} | {metrics.false_positives} | {metrics.false_negatives} | "
            f"{metrics.precision:.4f} | {metrics.recall:.4f} | {metrics.f1:.4f} | "
            f"{metrics.entity_accuracy:.4f} | {metrics.support} |"
        )
    return "\n".join(lines)


def _confusion_table(matrix: dict[str, dict[str, int]]) -> str:
    columns = sorted({column for row in matrix.values() for column in row})
    lines = [
        "| Actual \\ Predicted | " + " | ".join(columns) + " |",
        "| --- | " + " | ".join("---:" for _ in columns) + " |",
    ]
    for actual in sorted(matrix):
        lines.append(f"| {actual} | " + " | ".join(str(matrix[actual].get(column, 0)) for column in columns) + " |")
    return "\n".join(lines)


def _plain_report_text(report: EvaluationReport) -> str:
    return "\n".join(
        [
            "Evaluation Report",
            "",
            f"Precision: {report.overall.precision:.4f}",
            f"Recall: {report.overall.recall:.4f}",
            f"F1: {report.overall.f1:.4f}",
            f"Entity Accuracy: {report.overall.entity_accuracy:.4f}",
        ]
    )


def _write_minimal_pdf(path: str, content: str) -> None:
    escaped = content[:3000].replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 36 780 Td 12 TL ({escaped}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj",
    ]
    body = "%PDF-1.4\n" + "\n".join(objects) + "\n%%EOF\n"
    Path(path).write_bytes(body.encode("latin-1", errors="replace"))
