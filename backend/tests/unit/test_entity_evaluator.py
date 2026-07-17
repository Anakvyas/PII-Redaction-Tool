from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemas.common import PIIType
from evaluation.entity_evaluator import (
    EvaluationEntity,
    evaluate_entities,
    formulas,
    generate_annotation_template,
    load_entities,
    match_entities,
    metrics_from_counts,
    write_csv_report,
    write_json_report,
    write_markdown_report,
    write_pdf_report,
    write_reports,
)


def _gt(pii_type: PIIType, start: int, end: int, document_id: str = "default", text: str | None = None) -> EvaluationEntity:
    return EvaluationEntity(pii_type=pii_type, start=start, end=end, document_id=document_id, text=text)


# -- metrics_from_counts -------------------------------------------------


def test_metrics_from_counts_computes_precision_recall_f1_and_accuracy() -> None:
    metrics = metrics_from_counts(tp=8, fp=2, fn=2)

    assert metrics.precision == pytest.approx(0.8)
    assert metrics.recall == pytest.approx(0.8)
    assert metrics.f1 == pytest.approx(0.8)
    assert metrics.entity_accuracy == pytest.approx(8 / 12)
    assert metrics.support == 10


def test_metrics_from_counts_handles_zero_division() -> None:
    metrics = metrics_from_counts(tp=0, fp=0, fn=0)

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0
    assert metrics.entity_accuracy == 0.0
    assert metrics.support == 0


# -- match_entities / evaluate_entities -----------------------------------


def test_match_entities_classifies_true_positive_false_positive_and_false_negative() -> None:
    ground_truth = [
        _gt(PIIType.PERSON, 0, 8, text="Jane Doe"),  # matched -> TP
        _gt(PIIType.EMAIL, 20, 34, text="missed@example.com"),  # unmatched -> FN
    ]
    predictions = [
        _gt(PIIType.PERSON, 0, 8, text="Jane Doe"),  # overlaps GT[0], same type -> TP
        _gt(PIIType.COMPANY, 50, 57, text="Initech"),  # no overlap -> FP
    ]

    matches = match_entities(ground_truth, predictions)
    outcomes = sorted(m.outcome for m in matches)

    assert outcomes == ["false_negative", "false_positive", "true_positive"]


def test_evaluate_entities_reports_overall_and_per_type_counts() -> None:
    ground_truth = [
        _gt(PIIType.PERSON, 0, 8),
        _gt(PIIType.PERSON, 20, 28),
        _gt(PIIType.EMAIL, 40, 54),
    ]
    predictions = [
        _gt(PIIType.PERSON, 0, 8),  # TP (person)
        _gt(PIIType.PERSON, 100, 108),  # FP (person) - no overlap
        # GT[1] person and GT[2] email both unmatched -> FN person, FN email
    ]

    report = evaluate_entities(ground_truth, predictions)

    assert report.overall.true_positives == 1
    assert report.overall.false_positives == 1
    assert report.overall.false_negatives == 2

    assert report.per_type[PIIType.PERSON].true_positives == 1
    assert report.per_type[PIIType.PERSON].false_positives == 1
    assert report.per_type[PIIType.PERSON].false_negatives == 1
    assert report.per_type[PIIType.EMAIL].false_negatives == 1
    assert report.per_type[PIIType.EMAIL].true_positives == 0

    assert report.classification_report["person"] == report.per_type[PIIType.PERSON]


def test_evaluate_entities_counts_type_mismatch_as_fn_for_expected_and_fp_for_predicted() -> None:
    ground_truth = [_gt(PIIType.PERSON, 0, 8)]
    predictions = [_gt(PIIType.COMPANY, 0, 8)]  # overlaps span, wrong type

    report = evaluate_entities(ground_truth, predictions)

    assert report.per_type[PIIType.PERSON].false_negatives == 1
    assert report.per_type[PIIType.PERSON].true_positives == 0
    assert report.per_type[PIIType.COMPANY].false_positives == 1
    assert report.per_type[PIIType.COMPANY].true_positives == 0
    assert report.confusion_matrix["person"]["company"] == 1


def test_evaluate_entities_respects_document_id_boundaries() -> None:
    ground_truth = [_gt(PIIType.PERSON, 0, 8, document_id="doc-a")]
    predictions = [_gt(PIIType.PERSON, 0, 8, document_id="doc-b")]

    report = evaluate_entities(ground_truth, predictions)

    assert report.overall.true_positives == 0
    assert report.overall.false_positives == 1
    assert report.overall.false_negatives == 1


# -- load_entities ---------------------------------------------------------


def test_load_entities_accepts_bare_list_with_nested_span(tmp_path) -> None:
    path = tmp_path / "entities.json"
    path.write_text(
        json.dumps(
            [
                {"pii_type": "person", "span": {"start": 0, "end": 4}, "text": "Jane"},
                {"entity_type": "email", "start": 10, "end": 24, "text": "jane@example.com"},
            ]
        ),
        encoding="utf-8",
    )

    entities = load_entities(str(path))

    assert entities[0].pii_type == PIIType.PERSON
    assert entities[0].start == 0 and entities[0].end == 4
    assert entities[1].pii_type == PIIType.EMAIL
    assert entities[1].document_id == "default"


def test_load_entities_accepts_object_with_entities_key_and_alternate_type_field(tmp_path) -> None:
    path = tmp_path / "entities.json"
    path.write_text(
        json.dumps(
            {
                "entities": [
                    {"label": "company", "start": 5, "end": 12, "document_id": "doc-1"},
                ]
            }
        ),
        encoding="utf-8",
    )

    entities = load_entities(str(path))

    assert len(entities) == 1
    assert entities[0].pii_type == PIIType.COMPANY
    assert entities[0].document_id == "doc-1"


def test_load_entities_rejects_unsupported_type(tmp_path) -> None:
    path = tmp_path / "entities.json"
    path.write_text(json.dumps([{"pii_type": "not_a_real_type", "start": 0, "end": 1}]), encoding="utf-8")

    try:
        load_entities(str(path))
        assert False, "expected ValueError for unsupported pii_type"
    except ValueError:
        pass


# -- generate_annotation_template -------------------------------------------


def test_generate_annotation_template_prefills_from_predictions(tmp_path) -> None:
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(
        json.dumps([{"pii_type": "person", "start": 0, "end": 4, "text": "Jane"}]),
        encoding="utf-8",
    )
    template_path = tmp_path / "ground_truth.json"

    generate_annotation_template(str(predictions_path), str(template_path))
    payload = json.loads(template_path.read_text(encoding="utf-8"))

    assert payload["entities"][0]["pii_type"] == "person"
    assert payload["entities"][0]["annotator_decision"] == "accept"
    assert "instructions" in payload


def test_generate_annotation_template_without_predictions_writes_empty_scaffold(tmp_path) -> None:
    template_path = tmp_path / "ground_truth.json"

    generate_annotation_template(None, str(template_path))
    payload = json.loads(template_path.read_text(encoding="utf-8"))

    assert payload["entities"] == []


# -- reports -----------------------------------------------------------------


def _sample_report():
    ground_truth = [_gt(PIIType.PERSON, 0, 8), _gt(PIIType.EMAIL, 20, 34)]
    predictions = [_gt(PIIType.PERSON, 0, 8)]
    return evaluate_entities(ground_truth, predictions)


def test_write_json_report_includes_metrics_confusion_matrix_and_formulas(tmp_path) -> None:
    report = _sample_report()
    path = tmp_path / "report.json"

    write_json_report(report, str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["overall"]["true_positives"] == 1
    assert "confusion_matrix" in payload
    assert payload["classification_report"]["person"]["true_positives"] == 1
    assert payload["formulas"] == formulas()


def test_write_csv_report_has_header_and_overall_row(tmp_path) -> None:
    report = _sample_report()
    path = tmp_path / "report.csv"

    write_csv_report(report, str(path))
    lines = path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("label,")
    assert any(line.startswith("overall,") for line in lines)


def test_write_markdown_report_includes_confusion_matrix_and_formula_section(tmp_path) -> None:
    report = _sample_report()
    path = tmp_path / "report.md"

    write_markdown_report(report, str(path))
    content = path.read_text(encoding="utf-8")

    assert "# Evaluation Report" in content
    assert "## Confusion Matrix" in content
    assert "## Formulas" in content
    assert "Precision" in content


def test_write_pdf_report_produces_a_pdf_file(tmp_path) -> None:
    report = _sample_report()
    path = tmp_path / "report.pdf"

    write_pdf_report(report, str(path))

    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")


def test_write_reports_generates_all_five_formats(tmp_path) -> None:
    report = _sample_report()

    paths = write_reports(report, str(tmp_path), prefix="run1")

    assert set(paths) == {"json", "csv", "markdown", "pdf"}
    for path in paths.values():
        assert Path(path).exists()


# -- formulas ------------------------------------------------------------


def test_formulas_documents_every_metric() -> None:
    docs = formulas()

    for key in ("true_positive", "false_positive", "false_negative", "precision", "recall", "f1", "entity_accuracy"):
        assert key in docs
        assert docs[key]
