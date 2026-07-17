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
    replacement_map_path: str
    audit_log_path: str
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
        artifact_dir = Path(output_path).parent
        artifact_stem = Path(output_path).stem
        replacement_map_path = str(artifact_dir / f"{artifact_stem}_replacement_map.json")
        audit_log_path = str(artifact_dir / f"{artifact_stem}_audit_log.json")

        if document_format == DocumentFormat.DOCX:
            redaction = redact_docx(source_path, output_path, approved, strategy_map)
        elif document_format == DocumentFormat.PDF:
            redaction = redact_pdf(source_path, output_path, approved, strategy_map)
        else:
            raise ValueError(f"Unsupported document format: {document_format}")

        redaction.faker_engine.write_artifacts(
            replacement_map_path=replacement_map_path,
            audit_log_path=audit_log_path,
            audit_entries=redaction.audit_entries,
        )

        return ReplacementResult(
            output_path=output_path,
            replacement_map_path=replacement_map_path,
            audit_log_path=audit_log_path,
            summary=build_summary(redaction.counts_by_type),
        )
