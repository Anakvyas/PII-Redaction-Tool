# PII Redaction Tool

Detects and redacts personal information (names, emails, phones, companies,
addresses, SSNs, credit cards, DOBs, IP addresses) from DOCX/PDF files,
replacing each one with a realistic fake value. Includes a CLI script (the
core deliverable), a full web app on top of it, and an evaluation report.

## Approach

Five detectors run together and corroborate each other: **regex** for
fixed-shape data (SSN, credit card, phone, email, IP, address — Luhn-checked
cards, range-checked IPs), a **date heuristic** for DOB (a date only counts
if "date of birth"/"DOB" appears nearby), **spaCy NER** and **Microsoft
Presidio** for person/company names, and a **labeled-field detector** we
added after finding spaCy/Presidio miss names in short "Label: Value" text
("Applicant: Rashi Patil") even though they handle full sentences fine.
Matches are merged by confidence, with a rule that a hard regex match always
wins over a fuzzy NER guess covering the same text. Replacements are
generated with **Faker**, with a stable mapping so every occurrence of a
name becomes the same fake name (and linked email/phone stay consistent).
DOCX/PDF formatting (fonts, bold, tables, headers) is preserved because only
matched text is swapped in place — nothing else is touched. Embedded images
(e.g. a scanned ID card) are also OCR'd (Tesseract) and redacted, in English
only.

Run it: `cd backend && python scripts/redact.py --input file.docx --output-dir out/`

## Tradeoffs, false positives & false negatives

- **False positives**: legal/financial documents capitalize their own terms
  ("the Company", "the Board") and NER tags them as organizations. Mitigated
  with confidence discounts, not eliminated. spaCy also occasionally tags
  Indian place names as PERSON.
- **False negatives**: multi-line addresses (street/city/state on separate
  lines) aren't reconstructed into one match. Two names separated by "/"
  sometimes merge into one, dropping the second. Devanagari (Hindi) text in
  images isn't detected at all — OCR and NER here are English-only.
- We chose to redact phone numbers and IP addresses too (the assignment
  lists them as required), and to skip order/ticket numbers and non-birth
  dates as not PII.

## Evaluation

**Method**: ran the full pipeline against the assignment's real source
document (a ~300-page Indian IPO prospectus), then hand-checked a
representative, dense slice against the source by hand (39 ground-truth
entities — names, emails, phones, companies, addresses) since verifying
all ~2,200 detections across the whole document by hand isn't practical.
Full methodology and numbers: `deliverables/README.md`.

**Results** (precision / recall / F1):

| Type | Precision | Recall | F1 |
|---|---|---|---|
| Email | 1.00 | 1.00 | 1.00 |
| Phone | 0.75 | 1.00 | 0.86 |
| Person | 0.54 | 0.54 | 0.54 |
| Company | 0.07 | 1.00 | 0.12 |
| Address | 0.09 | 0.29 | 0.13 |
| **Overall** | **0.18** | **0.59** | **0.27** |

Company/address precision is low because legal boilerplate text ("the
Offer for Sale", "Book Running Lead Managers") reads as company-shaped to
NER — every *real* company name was still found (100% recall). Full
confusion matrix: `deliverables/eval/evaluation_report.md`.

## Repo layout

- `backend/` — FastAPI + detection/redaction pipeline. `scripts/redact.py`
  is the standalone CLI (no server needed). `scripts/evaluate.py` scores
  any ground-truth vs. predictions pair.
- `frontend/` — Next.js web app (upload, review, redact, evaluation
  dashboard).
- `deliverables/` — the actual run against the assignment's document
  (kept out of git — see below).

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_lg
cp .env.example .env
uvicorn main:app --reload
```

```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL
npm run dev
```

## Deploy

**Backend (Render)**: New Web Service → Docker runtime → point at
`backend/Dockerfile` → set env vars `API_KEY`, `SECRET_KEY`, `CORS_ORIGINS`
(your Vercel URL), `DATABASE_URL` (Render Postgres, optional — defaults to
SQLite).

**Frontend (Vercel)**: Import repo, root directory `frontend/` → set
`NEXT_PUBLIC_API_URL` to your Render backend URL + `/api/v1`, and
`NEXT_PUBLIC_API_KEY` matching the backend's `API_KEY`.

## Note on `deliverables/`

Contains the real source document and results. The source document has two
embedded scanned ID cards belonging to real third parties — kept out of git
(`.gitignore`) rather than pushed. See `deliverables/README.md`.
