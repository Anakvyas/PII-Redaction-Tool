"""CLI helper for entity-level PII evaluation.

Compares a ground-truth entities JSON file against a predictions entities
JSON file and writes JSON/CSV/Markdown/PDF reports (confusion matrix,
classification report, precision/recall/entity accuracy).

If the ground-truth file does not exist yet, an annotation template is
generated at that path instead (pre-filled from --predictions when given)
so a human can label it and re-run this command.

Examples:
    python scripts/evaluate.py --ground-truth gt.json --predictions pred.json --output-dir reports/
    python scripts/evaluate.py --ground-truth gt.json --predictions pred.json --explain
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.entity_evaluator import (  # noqa: E402
    evaluate_entities,
    formulas,
    generate_annotation_template,
    load_entities,
    write_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ground-truth", required=True, help="Path to the ground-truth entities JSON file.")
    parser.add_argument("--predictions", required=True, help="Path to the model predictions entities JSON file.")
    parser.add_argument("--output-dir", default="evaluation_reports", help="Directory to write reports into.")
    parser.add_argument("--prefix", default="evaluation", help="Filename prefix for generated reports.")
    parser.add_argument("--explain", action="store_true", help="Print the scoring formulas and exit.")
    args = parser.parse_args(argv)

    if args.explain:
        _print_formulas()
        return 0

    ground_truth_path = Path(args.ground_truth)
    if not ground_truth_path.exists():
        predictions_path = Path(args.predictions)
        source = str(predictions_path) if predictions_path.exists() else None
        generate_annotation_template(source, str(ground_truth_path))
        print(f"No ground truth found at {ground_truth_path}.")
        if source:
            print(f"Generated an annotation template there, pre-filled from {predictions_path}.")
        else:
            print(f"Generated a blank annotation template there ({predictions_path} was also not found).")
        print("Review it — correct pii_type/start/end/text, delete false positives, add missed")
        print("entities — then re-run this command with the same --ground-truth path.")
        return 0

    ground_truth = load_entities(str(ground_truth_path))
    predictions = load_entities(args.predictions)
    report = evaluate_entities(ground_truth, predictions)
    paths = write_reports(report, args.output_dir, prefix=args.prefix)

    print(f"Compared {len(ground_truth)} ground-truth entities against {len(predictions)} predictions.")
    print(
        f"Overall -- precision: {report.overall.precision:.4f}, recall: {report.overall.recall:.4f}, "
        f"f1: {report.overall.f1:.4f}, entity accuracy: {report.overall.entity_accuracy:.4f}"
    )
    print(
        f"TP={report.overall.true_positives} FP={report.overall.false_positives} "
        f"FN={report.overall.false_negatives}"
    )
    print("Reports written:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    return 0


def _print_formulas() -> None:
    print("Scoring formulas:")
    for name, formula in formulas().items():
        print(f"  {name}: {formula}")


if __name__ == "__main__":
    raise SystemExit(main())
