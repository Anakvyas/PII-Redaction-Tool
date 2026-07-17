"""Span-overlap precision/recall/F1 — the same measure any NER system is
scored with. A predicted span counts as a true positive if it overlaps an
as-yet-unmatched expected span of the same type; matching is greedy and
each expected span can be claimed by at most one prediction."""
from __future__ import annotations

from dataclasses import dataclass

from schemas.common import TextSpan


@dataclass
class Metrics:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def metrics_from_counts(tp: int, fp: int, fn: int) -> Metrics:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return Metrics(precision=precision, recall=recall, f1=f1, true_positives=tp, false_positives=fp, false_negatives=fn)


def compute_metrics(predicted: list[TextSpan], expected: list[TextSpan]) -> Metrics:
    matched_expected: set[int] = set()
    true_positives = 0
    for p in predicted:
        for i, e in enumerate(expected):
            if i in matched_expected:
                continue
            if p.start < e.end and e.start < p.end:
                matched_expected.add(i)
                true_positives += 1
                break
    false_positives = len(predicted) - true_positives
    false_negatives = len(expected) - len(matched_expected)
    return metrics_from_counts(true_positives, false_positives, false_negatives)
