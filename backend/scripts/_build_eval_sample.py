"""One-off helper: build the ground-truth + prediction JSON files for the
evaluation report against a representative, hand-verified slice of the real
assignment document (the "General Information" section of the Red Herring
Prospectus — company/registrar/director/officer/lead-manager contact block).

Not part of the shipped CLI surface — this is how deliverables/eval/*.json
were produced, kept for reproducibility. Run once from backend/:
    python scripts/_build_eval_sample.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.container import get_detection_pipeline  # noqa: E402
from schemas.common import DocumentFormat, ExtractedDocument, PIIType, TextBlock
from services.extraction.docx_extractor import DocxExtractor

SOURCE = "../deliverables/input/red_herring_prospectus.docx"
OUT_DIR = Path("../deliverables/eval")
SAMPLE_NAME = "general_information_section"


def extract_sample() -> str:
    extracted = DocxExtractor().extract(SOURCE, "doc-1")
    text = extracted.flattened_text()
    start = text.find("GENERAL INFORMATION\n")
    end = text.find("SEBI registration no.: INM000011179") + len("SEBI registration no.: INM000011179")
    assert start >= 0 and end > start
    return text[start:end]


def gt_entity(pii_type: PIIType, sample: str, substring: str, occurrence: int = 0) -> dict:
    """Locate the nth occurrence of `substring` in `sample` and emit a
    ground-truth entity record. Raises if the substring isn't found —
    fail loudly rather than silently mis-annotating."""
    idx = -1
    for _ in range(occurrence + 1):
        idx = sample.index(substring, idx + 1)
    return {
        "pii_type": pii_type.value,
        "start": idx,
        "end": idx + len(substring),
        "text": substring,
        "document_id": SAMPLE_NAME,
    }


def build_ground_truth(sample: str) -> list[dict]:
    entities: list[dict] = []

    persons = [
        "Kushal Subbayya Hegde",
        "Rajesh Kushal Hegde",
        "Rohit Kushal Hegde",
        "Rakhi Girija Shetty",
        "Dinesh Hirachand Munot",
        "Ajay Shriram Patil",
        "Ram Kumar Tiwari",
        "Indu Jacob",
        "Sarthak Malvadkar",
        "Lokesh Shah",
        "Soumavo Sarkar",
        "Kishan Rastogi",
        "Abhijit Diwan",
    ]
    for name in persons:
        entities.append(gt_entity(PIIType.PERSON, sample, name))

    emails = [
        "Sarthak.malvadkar@kshinterantional.com",
        "ksh.ipo@nuvama.com",
        "customerservice.mb@nuvama.com",
        "ksh@icicisecurities.com",
        "customercare@icicisecurities.com",
    ]
    for email in emails:
        entities.append(gt_entity(PIIType.EMAIL, sample, email))

    phones = ["+ 91 20 45053237", "+91 22 40094400", "+91 22 6807 7100"]
    for phone in phones:
        entities.append(gt_entity(PIIType.PHONE, sample, phone))

    # "KSH International Limited" appears twice (registered + corporate office).
    entities.append(gt_entity(PIIType.COMPANY, sample, "KSH International Limited", occurrence=0))
    entities.append(gt_entity(PIIType.COMPANY, sample, "KSH International Limited", occurrence=1))
    entities.append(gt_entity(PIIType.COMPANY, sample, "Nuvama Wealth Management Limited"))
    entities.append(gt_entity(PIIType.COMPANY, sample, "ICICI Securities Limited"))
    # Explicit judgment call: "Registrar of Companies, Maharashtra at Pune" is a
    # government regulatory office, not a commercial company — excluded.

    addresses = [
        "11/3, 11/4 and 11/5, Village Birdewadi Chakan, Taluka-Khed\n\nPune – 410 501\n\nMaharashtra, India",
        "201, Tower-2, Montreal Business Centre Off Pallod Farms, Baner\n\nPune 411 045 Maharashtra, India",
        "PCNTDA Green Building Block A 1st and 2nd floor Near Akurdi Railway Station Akurdi, "
        "Pune – 411 044 Maharashtra, India",
        "S. no. 245/ 104, Pushpakamal, Deccan Gymkhana Society, lane no. 3 Prabhat Road, opposite "
        "PYC basketball court, Deccan Gymkhana, Pune – 411 004 Maharashtra, India",
        "12 Buena Monte, NCL co-operative housing society, Panchvati, Pashan, Pune – 411 008, Maharashtra, India",
        "Pushpakamal Apartment, Flat – 1, S. no. 245/ 104, Prabhat Road Lane no. 3, Shivaji Nagar, "
        "Deccan Gymkhana, Pune – 411 004, Maharashtra, India",
        "S. no. 245/ 104, Pushpakamal, Deccan Gymkhana Society, lane no.\n\n"
        "3 Prabhat Road, opposite PYC basketball court, Erandawane, Deccan Gymkhana, "
        "Pune – 411 004 Maharashtra, India",
        "Pratik Bunglow, Senapati Bapat Road, behind Sahara Hotel, Shivajinagar, Model Colony, "
        "Pune – 411 016, Maharashtra, India",
        "602, Gopalkrupa Apartment, Bhonde colony, Prabhat Road, Erandawane, Pune – 411 004, Maharashtra, India",
        "A-259, JK Road, Minal Residency, Huzur, Govindpura, Bhopal – 462 023, Madhya Pradesh, India",
        "A29, Abhimanshree Society, Pashan Road, Pune – 411 008, Maharashtra, India",
        "Gat No. 11/3, 11/4, 11/5, Village Birdewadi\n\nTaluka Khed, District Pune – 410 501\n\nMaharashtra, India",
        "801-804, Wing A, Building No. 3 Inspire BKC G Block, Bandra Kurla Complex\n\n"
        "Bandra East, Mumbai – 400 051 Maharashtra, India",
        "ICICI Venture House Appasaheb Marathe Marg Prabhadevi, Mumbai – 400 025 Maharashtra, India",
    ]
    for address in addresses:
        entities.append(gt_entity(PIIType.ADDRESS, sample, address))

    entities.sort(key=lambda e: e["start"])
    return entities


def build_predictions(sample: str) -> list[dict]:
    document = ExtractedDocument(
        document_id=SAMPLE_NAME, format=DocumentFormat.DOCX, blocks=[TextBlock(text=sample, char_offset=0)]
    )
    entities = get_detection_pipeline().run(document, set(PIIType))
    return [
        {
            "pii_type": e.pii_type.value,
            "start": e.span.start,
            "end": e.span.end,
            "text": e.raw_value,
            "confidence": e.confidence,
            "source_detector": e.source_detector,
            "document_id": SAMPLE_NAME,
        }
        for e in entities
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample = extract_sample()
    (OUT_DIR / "sample_text.txt").write_text(sample, encoding="utf-8")

    ground_truth = build_ground_truth(sample)
    (OUT_DIR / "ground_truth.json").write_text(
        json.dumps({"entities": ground_truth}, indent=2), encoding="utf-8"
    )

    predictions = build_predictions(sample)
    (OUT_DIR / "predictions.json").write_text(
        json.dumps({"entities": predictions}, indent=2), encoding="utf-8"
    )

    print(f"sample: {len(sample)} chars")
    print(f"ground truth entities: {len(ground_truth)}")
    print(f"prediction entities: {len(predictions)}")


if __name__ == "__main__":
    main()
