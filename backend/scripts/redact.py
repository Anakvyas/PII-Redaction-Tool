"""Standalone PII redaction script.

Reads a single DOCX or PDF file, detects PII with the same multi-engine
pipeline the web app uses (regex, spaCy NER, and Microsoft Presidio, merged
with confidence-corroboration across detectors), replaces every entity above
the confidence floor according to the chosen strategy, and writes the
redacted file plus a replacement map and an audit log. No server, no
database, no manual review step — a single automated pass end to end.

Usage:
    python scripts/redact.py --input document.docx --output-dir out/
    python scripts/redact.py --input document.pdf  --output-dir out/ --strategy mask
    python scripts/redact.py --input document.docx --output-dir out/ \\
        --pii-types person,email,phone --confidence-floor 0.8
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.container import get_detection_pipeline  # noqa: E402
from replacement.pipeline import ReplacementPipeline  # noqa: E402
from schemas.common import DocumentFormat, ExtractedDocument, PIIType, RedactionStrategy  # noqa: E402
from services.extraction import get_extractor  # noqa: E402
from utils.files import format_from_filename  # noqa: E402

_ALL_TYPES = tuple(t.value for t in PIIType)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Path to the source .docx or .pdf file.")
    parser.add_argument("--output-dir", default="redaction_output", help="Directory to write outputs into.")
    parser.add_argument(
        "--strategy",
        default="pseudonymize",
        choices=[s.value for s in RedactionStrategy],
        help="Replacement strategy applied to every detected entity (default: pseudonymize, "
        "i.e. realistic fake values via Faker — matches the assignment's example).",
    )
    parser.add_argument(
        "--pii-types",
        default=",".join(_ALL_TYPES),
        help=f"Comma-separated PII types to detect (default: all — {', '.join(_ALL_TYPES)}).",
    )
    parser.add_argument(
        "--confidence-floor",
        type=float,
        default=0.75,
        help="Minimum detector confidence to auto-redact without human review (default: 0.75).",
    )
    args = parser.parse_args(argv)

    source_path = Path(args.input)
    if not source_path.exists():
        parser.error(f"Input file not found: {source_path}")

    requested_types = {PIIType(t.strip()) for t in args.pii_types.split(",") if t.strip()}
    strategy = RedactionStrategy(args.strategy)
    strategy_map = {t.value: strategy.value for t in requested_types}

    fmt = DocumentFormat(format_from_filename(source_path.name, (".docx", ".pdf")))
    extractor = get_extractor(fmt)
    extracted: ExtractedDocument = extractor.extract(str(source_path), document_id=source_path.stem)

    entities = get_detection_pipeline().run(extracted, requested_types)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = ReplacementPipeline().run(
        source_path=str(source_path),
        document_format=fmt,
        entities=entities,
        policy_strategy_map=strategy_map,
        confidence_floor=args.confidence_floor,
    )

    redacted_path = output_dir / f"{source_path.stem}_redacted{source_path.suffix}"
    map_path = output_dir / "replacement_map.json"
    audit_path = output_dir / "audit_log.json"
    shutil.copyfile(result.output_path, redacted_path)
    shutil.copyfile(result.replacement_map_path, map_path)
    shutil.copyfile(result.audit_log_path, audit_path)

    print(f"Detected {len(entities)} candidate entities across {len(requested_types)} requested PII types.")
    print(f"Redacted {result.summary.total_redacted} entities ({strategy.value} strategy):")
    for pii_type, count in sorted(result.summary.counts_by_type.items(), key=lambda kv: kv[0].value):
        print(f"  {pii_type.value:>12}: {count}")
    print()
    print("Wrote:")
    print(f"  {redacted_path}")
    print(f"  {map_path}")
    print(f"  {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
