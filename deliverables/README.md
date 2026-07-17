# Deliverables

The actual run against the assignment's source document: **KSH International
Limited's Red Herring Prospectus** (`input/red_herring_prospectus.docx`) — a
real, ~300-page, 76-table Indian IPO filing, not a synthetic sample.

## What's here

```
input/red_herring_prospectus.docx          the source document
output/red_herring_prospectus_redacted.docx  the full redacted document
output/replacement_map.json                 original -> replacement, whole document
output/audit_log.json                       full per-entity audit trail, whole document
eval/sample_text.txt                        the exact text slice scored below
eval/ground_truth.json                      hand-verified expected entities for that slice
eval/predictions.json                       what the pipeline actually detected
eval/evaluation_report.{json,csv,md,pdf}    precision/recall/F1/confusion matrix
```

Reproduce with:

```bash
cd backend
source .venv/bin/activate
python scripts/redact.py --input ../deliverables/input/red_herring_prospectus.docx --output-dir ../deliverables/output
python scripts/_build_eval_sample.py   # rebuilds eval/ground_truth.json + eval/predictions.json
python scripts/evaluate.py --ground-truth ../deliverables/eval/ground_truth.json --predictions ../deliverables/eval/predictions.json --output-dir ../deliverables/eval
```

## Full-document redaction

```
Detected 2,244 candidate entities across all 9 PII types.
Redacted 1,253 entities (pseudonymize strategy):
  company: 969   person: 197   email: 52   phone: 31   address: 4
```

No SSN, credit card, or DOB instances were redacted because the document
doesn't contain any — this is a corporate IPO filing, not a personal/financial
record, so recall for those three types couldn't be meaningfully exercised
against this particular document (see the bundled synthetic dataset in
`backend/evaluation/sample_dataset.py` for coverage of those types instead).

## Evaluation methodology

Hand-annotating ground truth across the full ~334,000-character, ~2,200-candidate
document isn't practical to do reliably by hand. Instead, this evaluates a
**representative, exhaustively-verified sample**: the document's "General
Information" section — the block that states the registered/corporate office,
the Board of Directors (name, designation, DIN, address per director, in a
table), the Company Secretary's contact details, and the two Book Running
Lead Managers' contact details (address, phone, email, named contact people).
It's dense with every PII type this section can contain (person, email, phone,
company, address) and small enough (5,960 characters, 39 ground-truth entities)
to check by hand against the source document, entity by entity.

This is an explicit scope choice, consistent with the assignment's framing —
it does not cover SSN/credit-card/DOB/IP-address (this section, and this
document, has none) or generalize precision/recall claims to the *entire*
document; it's the honest, verifiable slice.

## Results

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| **email** | 5 | 0 | 0 | **1.000** | **1.000** | **1.000** |
| **phone** | 3 | 1 | 0 | 0.750 | **1.000** | 0.857 |
| **person** | 7 | 6 | 6 | 0.538 | 0.538 | 0.538 |
| **company** | 4 | 57 | 0 | 0.066 | **1.000** | 0.123 |
| **address** | 4 | 43 | 10 | 0.085 | 0.286 | 0.131 |
| **overall** | 23 | 107 | 16 | 0.177 | 0.590 | 0.272 |

Full confusion matrix and classification report: `eval/evaluation_report.md`.

### Reading these numbers honestly, by type

**Email and phone** are exactly what a format-anchored regex/Presidio
approach should deliver: perfect or near-perfect. The one phone false
positive is a director's DIN (`05293084`, an 8-digit ID) misread as a phone
fragment — a real, minor precision gap, not a systemic one.

**Person: 53.8% precision and recall.** Of the 6 false negatives: 2 are a
formatting artifact ("Lokesh Shah/ Soumavo Sarkar" — two people listed with
a slash separator, both merged by NER into one span and then that span
mistyped as COMPANY rather than PERSON), 2 are genuine misses on short,
table-context names ("Kushal Subbayya Hegde" as the first table row, "Indu
Jacob"), and 2 more are the same slash-merge issue. The 6 false positives
are mostly place names inside addresses ("Taluka-Khed", "Shivaji Nagar",
"Erandawane") that spaCy's NER tagged PERSON instead of location — a known,
disclosed spaCy weakness on Indian place names, not something this project's
regex/heuristic layers can structurally fix without a location gazetteer
(out of scope here, but the clear next step if this were extended).

**Company: 100% recall, 6.6% precision.** Every real company name (`KSH
International Limited` ×2, `Nuvama Wealth Management Limited`, `ICICI
Securities Limited`) was found. But this section's text includes a full
paragraph of legal/procedural boilerplate ("Investor grievances") dense with
capitalized defined terms — `Registrar`, `Anchor Investors`, `Book Running
Lead Managers`, `PAN`, `UPI ID`, `ASBA Account`, `the Anchor Investor
Application Form` — that spaCy/Presidio's ORG recognizer tags as
organizations. This is a genuine, disclosed limitation of general-purpose
NER on legal/financial prose, not a bug: these models weren't trained to
distinguish "a company" from "a capitalized defined term in a contract."
Two targeted mitigations are already in the codebase
(`utils/fuzzy.py::adjust_company_confidence` discounts bare generic
self-references and phrases preceded by "the"/"our"/"this" with no company
suffix) and measurably reduced the false-positive count on the full document
(1,031 → 969 after the second fix alone) — but eliminating it fully would
need either a real legal-defined-terms gazetteer per document (most
prospectuses define their terms in a dedicated section) or a proper legal-NLP
model, both out of scope for this assignment's time budget.

**Address: 28.6% recall, 8.5% precision.** The real, disclosed limitation
here: Indian addresses in this document are split across separate lines —
street on one line, city+PIN on the next, state on the one after. The regex
detector matches structured single-line patterns (`number + street + suffix
+ optional city/state/zip`); it was never going to reconstruct a three-
paragraph address into one span, so scoring against "the whole logical
address as one entity" produces a harsh mismatch by construction. In
practice the detector still fragments-and-catches *pieces* of these
addresses (street lines, city names) — meaning real information is still
redacted, just not as one clean unit — visible in the confusion matrix as
address ground truth frequently landing on `company` predictions instead
(a street name like "Senapati Bapat Road" or a housing society name like
"Deccan Gymkhana Society" reads as plausibly-a-company-name to NER, same
underlying cause as the company precision issue above). A structurally
correct fix (merging consecutive short address-shaped lines into one
candidate before regex matching) is the clear next step, not attempted here
given time constraints — documented rather than quietly worked around.

## Bugs found and fixed by running this real document through the pipeline

Testing against synthetic data alone would have missed all of these —
they only surfaced against real, messy, non-US-formatted content:

1. **Address regex silently dropped any address with a 6-digit postal
   code** (India's PIN, vs. the US's 5-digit ZIP the regex assumed) — the
   truncated match then failed a downstream word-boundary safety check and
   the whole address vanished, not just the postal code.
2. **Company name spans lost their trailing legal suffix** ("Vertex
   Industries Pvt." instead of "…Pvt. Ltd.") inconsistently, depending on
   what followed in the text — a spaCy/Presidio tokenization quirk around
   abbreviation periods.
3. **spaCy/Presidio return zero PERSON entities** for names in short,
   label-prefixed, sentence-less text ("Applicant: Rashi Patil") even when
   the same model handles the same name correctly in a full sentence — added
   a deterministic labeled-field fallback detector for this specific,
   verified gap.
4. **That new fallback detector then over-triggered** on real legal
   text — "Promoter Selling Shareholders" and "Director Identification
   Number" are defined legal terms, not "Label: Name" fields, and a bare
   "Promoter"/"Director" trigger without a required colon matched them as if
   they were. Fixed by requiring a literal colon for the single-word,
   ambiguous triggers.
5. **A whole class of company false positives** — bare numbers, roman
   numerals (page references), a currency symbol, and legal self-references
   ("the Company", "the Board", "the Offer") tagged as organizations —
   plus the broader **defined-term-after-an-article** pattern described
   above.
6. **The most severe: an entire table's data was silently dropped from
   extraction.** The Board of Directors table (8 real people — name,
   designation, government ID, home address) extracted only the Name
   column; every other cell in every data row vanished. Root cause:
   `_iter_table_cells`'s merged-cell deduplication tracked `id(cell._tc)`
   — a memory address — instead of the cell object itself. `row.cells`
   builds a fresh wrapper object on each access; once the previous cell's
   wrapper was garbage collected, CPython was free to recycle its exact
   memory address for the *next* cell's wrapper, making two completely
   different cells compare as "the same cell already seen." This affected
   every table in the document with enough cells to trigger the recycling
   (confirmed: all 76). Fixed by keeping the actual cell elements alive in
   the dedup set instead of just their id()s. Extracted text length jumped
   from ~301,000 to ~333,700 characters on this document alone.

All six have regression tests in `backend/tests/unit/` (`test_regex_detector.py`,
`test_detection_pipeline.py`, `test_labeled_field_detector.py`, `test_fuzzy.py`,
`test_docx_redactor.py`) proving both the failure mode and the fix.
