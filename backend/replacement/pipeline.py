"""Orchestrates the replacement pipeline: filter to approved detections, pick
the format-specific redactor, and package the result with a summary report."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from replacement.docx_redactor import redact_docx
from replacement.pdf_redactor import redact_pdf
from report.summary import RedactionSummary, build_summary
from schemas.common import DocumentFormat, PIIEntity, PIIType, RedactionStrategy


@dataclass
class ReplacementResult:
    output_path: str
    summary: RedactionSummary


class ReplacementPipeline:
    def run(
        self,
        source_path: str,
        document_format: DocumentFormat,
        entities: list[PIIEntity],
        policy_strategy_map: dict[str, str],
        confidence_floor: float,
    ) -> ReplacementResult:
        strategy_map = {PIIType(k): RedactionStrategy(v) for k, v in policy_strategy_map.items()}
        approved = [e for e in entities if e.is_approved(confidence_floor)]

        suffix = Path(source_path).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            output_path = tmp.name

        if document_format == DocumentFormat.DOCX:
            counts = redact_docx(source_path, output_path, approved, strategy_map)
        elif document_format == DocumentFormat.PDF:
            counts = redact_pdf(source_path, output_path, approved, strategy_map)
        else:
            raise ValueError(f"Unsupported document format: {document_format}")

        return ReplacementResult(output_path=output_path, summary=build_summary(counts))
