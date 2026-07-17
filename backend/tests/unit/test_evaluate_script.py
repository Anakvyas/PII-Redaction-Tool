from __future__ import annotations

import json

from scripts.evaluate import main


def test_main_generates_annotation_template_when_ground_truth_missing(tmp_path, capsys) -> None:
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(
        json.dumps([{"pii_type": "person", "start": 0, "end": 4, "text": "Jane"}]),
        encoding="utf-8",
    )
    ground_truth_path = tmp_path / "ground_truth.json"

    exit_code = main(
        [
            "--ground-truth",
            str(ground_truth_path),
            "--predictions",
            str(predictions_path),
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert ground_truth_path.exists()
    payload = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    assert payload["entities"][0]["pii_type"] == "person"
    assert "annotation template" in out.lower()


def test_main_runs_full_comparison_when_ground_truth_present(tmp_path, capsys) -> None:
    ground_truth_path = tmp_path / "ground_truth.json"
    predictions_path = tmp_path / "predictions.json"
    output_dir = tmp_path / "reports"

    ground_truth_path.write_text(
        json.dumps([{"pii_type": "person", "start": 0, "end": 4, "text": "Jane"}]),
        encoding="utf-8",
    )
    predictions_path.write_text(
        json.dumps([{"pii_type": "person", "start": 0, "end": 4, "text": "Jane"}]),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--ground-truth",
            str(ground_truth_path),
            "--predictions",
            str(predictions_path),
            "--output-dir",
            str(output_dir),
            "--prefix",
            "run1",
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert (output_dir / "run1_report.json").exists()
    assert (output_dir / "run1_report.csv").exists()
    assert (output_dir / "run1_report.md").exists()
    assert (output_dir / "run1_report.pdf").exists()
    assert "precision: 1.0000" in out


def test_main_explain_prints_formulas_without_requiring_files(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "--ground-truth",
            str(tmp_path / "missing_gt.json"),
            "--predictions",
            str(tmp_path / "missing_pred.json"),
            "--explain",
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "precision" in out.lower()
    assert not (tmp_path / "missing_gt.json").exists()
