"""Redaction summary report: what was found and what was actually redacted,
surfaced to the API/UI and useful for the audit trail."""
from __future__ import annotations

from dataclasses import dataclass, field

from schemas.common import PIIType


@dataclass
class RedactionSummary:
    counts_by_type: dict[PIIType, int] = field(default_factory=dict)

    @property
    def total_redacted(self) -> int:
        return sum(self.counts_by_type.values())


def build_summary(counts_by_type: dict[PIIType, int]) -> RedactionSummary:
    return RedactionSummary(counts_by_type=counts_by_type)


def render_text_report(summary: RedactionSummary, job_id: str) -> str:
    lines = [f"Redaction report for job {job_id}", "-" * 40]
    if not summary.counts_by_type:
        lines.append("No PII was redacted.")
        return "\n".join(lines)
    for pii_type, count in sorted(summary.counts_by_type.items(), key=lambda kv: kv[0].value):
        lines.append(f"{pii_type.value:<14} {count}")
    lines.append("-" * 40)
    lines.append(f"{'total':<14} {summary.total_redacted}")
    return "\n".join(lines)
