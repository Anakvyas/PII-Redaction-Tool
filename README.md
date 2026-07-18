# 🔒 PII Redaction Tool

A full-stack tool that detects and redacts personal information (PII) from
DOCX/PDF documents — built with a **Next.js** frontend and a **Python +
FastAPI** backend, using **spaCy**, **Microsoft Presidio**, and **Tesseract
OCR** for detection, and **Faker** for realistic fake replacements.

![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

## 🔗 Live Demo

|                  | Link                                         |
| ---------------- | -------------------------------------------- |
| 🌐 Frontend      | https://pii-redaction-tool-livid.vercel.app  |
| ⚙️ Backend API | https://pii-redaction-tool-99vj.onrender.com |

> ⚠️ **First load notice**: if the backend is on Render's free tier, it
> spins down after 15 minutes of inactivity. The first request after that
> takes 30–50s to wake up — this is a Render free-tier limitation, not a bug.

> 🚨 **Large document notice**: very large or table-dense documents (200+
> pages, dozens of tables) can still crash on Render's free tier (512MB
> RAM), even though detection itself runs in memory-bounded chunks (see
> `services/detection_service.py`) so its memory no longer grows with
> document length. The ceiling comes from two **fixed** costs that are
> paid before detection ever starts — back-of-envelope, measured against a
> real 300-page / 76-table document:
>
> | Stage                                             |      Measured RSS |
> | ------------------------------------------------- | ----------------: |
> | Baseline (FastAPI process)                        |            ~15 MB |
> | + parsing the document (`python-docx`/`lxml`) |           ~270 MB |
> | + loading the spaCy model (one-time)              |           ~235 MB |
> | **Total before a single detector runs**     | **~520 MB** |
>
> That's already over the 512MB cap for a document this dense, before
> detection begins.

## ✨ Features

### 🔍 Detection

- 9 PII types: full names, emails, phones, companies, addresses, SSNs,
  credit cards, dates of birth, IP addresses
- 5 corroborating detectors: regex (format-anchored types), spaCy NER,
  Microsoft Presidio, a date/context heuristic, and a labeled-field
  fallback for names in "Label: Value" form text
- OCR (Tesseract) on images embedded inside documents

### 📝 Redaction

- DOCX and PDF supported, formatting fully preserved (fonts, bold, tables,
  headers) — only matched text is swapped in place
- Realistic fake replacements via Faker, with a stable mapping so every
  occurrence of a name/email/phone stays consistent
- Mask, pseudonymize, generalize, or black-box, per PII type

### 👀 Review & Web App

- Upload → detect → review each match (accept/reject/retype) → redact →
  download
- Side-by-side original/redacted preview with PII highlighted
- Evaluation dashboard: precision/recall/F1 charts, audit log viewer

## 🧪 Try It

```bash
python backend/scripts/redact.py --input yourfile.docx --output-dir out/
```

No server needed — this is the core CLI. The web app wraps the same engine.

## 🛠️ Tech Stack

### Frontend

| Technology               | Role                 |
| ------------------------ | -------------------- |
| Next.js 16 (App Router)  | UI & routing         |
| TypeScript               | Type safety          |
| Tailwind CSS + shadcn/ui | Styling & components |
| Framer Motion            | Animation            |
| Recharts                 | Evaluation charts    |
| react-pdf / mammoth      | Document preview     |

### Backend

| Technology                   | Role                         |
| ---------------------------- | ---------------------------- |
| FastAPI                      | REST API                     |
| spaCy + Microsoft Presidio   | NER-based PII detection      |
| Tesseract (pytesseract)      | OCR for embedded images      |
| Faker                        | Realistic fake replacements  |
| python-docx / PyMuPDF        | DOCX/PDF parsing & redaction |
| SQLAlchemy + SQLite/Postgres | Job/policy storage           |

## 📁 Project Structure

```
├── frontend/                 # Next.js app
│   └── src/
│       ├── app/               # Landing, workspace, evaluation dashboard
│       ├── components/        # Preview, review UI, charts
│       └── lib/                # API client, types
│
└── backend/                  # FastAPI app
    ├── detectors/             # regex, spaCy, Presidio, date, labeled-field
    ├── replacement/           # redaction engine + Faker mapping
    ├── services/              # extraction, image OCR, job orchestration
    ├── evaluation/            # ground-truth comparison + reports
    ├── scripts/               # redact.py (CLI), evaluate.py (CLI)
    └── tests/                 # 220+ unit tests
```

## 🚀 Running Locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_md
cp .env.example .env
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL
npm run dev
```

## 🌐 Environment Variables

**Backend `.env`**

```
API_KEY=              # optional; empty disables auth (local dev)
SECRET_KEY=            # signs download links
CORS_ORIGINS=["http://localhost:3000"]
DATABASE_URL=          # optional; defaults to local SQLite
```

**Frontend `.env.local`**

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_API_KEY=   # must match backend's API_KEY, if set
```

## 📊 Evaluation

Ran against a real ~300-page document (see `deliverables/` locally — not
committed, contains real third-party data from the source file). Numbers
from a hand-verified, representative sample:

| Type    | Precision | Recall | F1   |
| ------- | --------- | ------ | ---- |
| Email   | 1.00      | 1.00   | 1.00 |
| Phone   | 0.75      | 1.00   | 0.86 |
| Person  | 0.54      | 0.54   | 0.54 |
| Company | 0.07      | 1.00   | 0.12 |
| Address | 0.09      | 0.29   | 0.13 |

Every real company/email/phone was found (100% recall on those); company/
address precision is pulled down by legal boilerplate reading as
company-shaped text to NER. Full write-up: `deliverables/README.md`.

## 📌 Known Limitations

| Issue                                                       | Cause                                                    | Note                                            |
| ----------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------- |
| Legal terms flagged as companies ("the Board", "the Offer") | NER can't tell a defined legal term from a real org name | Discounted, not eliminated                      |
| Multi-line addresses not caught as one match                | Regex expects a single-line address                      | Fragments (city, street) are often still caught |
| Non-English (e.g. Devanagari) text in images not detected   | OCR/NER here are English-only                            | Would need a language-specific OCR pack + model |
| No face detection in images                                 | Out of scope                                             | ID card photos are left untouched by design     |
| Very large/table-dense docs can OOM on Render's free tier   | Parsing + model-load alone use ~520MB (see notice above) | Not a code bug — needs more host RAM           |

## 📄 License

Built for educational/assessment purposes.

## 🙌 Acknowledgements

- [spaCy](https://spacy.io) & [Microsoft Presidio](https://microsoft.github.io/presidio/)
- [Faker](https://faker.readthedocs.io)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
