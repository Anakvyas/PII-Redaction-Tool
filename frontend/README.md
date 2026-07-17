# Redactly — frontend

A Next.js frontend for the PII detection & redaction backend: upload a DOCX/PDF, review
detected PII with highlights over the real document, redact it, and inspect evaluation
metrics and the audit trail.

**Stack:** Next.js 16 (App Router, Turbopack) · TypeScript · Tailwind CSS v4 · shadcn/ui
(Base UI) · Framer Motion · Recharts · next-themes · react-pdf · mammoth

## Getting started

```bash
npm install
cp .env.example .env.local   # point at your backend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend (see `../backend`) must be
running and reachable at `NEXT_PUBLIC_API_URL`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | yes | Base URL of the FastAPI backend, including the `/api/v1` prefix (e.g. `http://localhost:8000/api/v1`). |
| `NEXT_PUBLIC_API_KEY` | only if the backend sets `API_KEY` | Sent as `X-API-Key` on every request. |

Both are read at build/runtime as `NEXT_PUBLIC_*` vars, so they're baked into the client
bundle — never put a secret in them.

## Project structure

```
src/app/                     Routes: landing (/), workspace (/workspace, /workspace/jobs/[jobId]), evaluation (/evaluation)
src/components/landing/      Marketing page sections
src/components/workspace/    Upload dropzone, policy/PII-type pickers
src/components/jobs/         Job list, stepper, status badge, detection review, downloads
src/components/preview/      PDF viewer (bbox highlight overlay), DOCX viewer (mammoth + text-match highlight overlay)
src/components/evaluation/   Stat tiles, charts, audit log table
src/lib/                     Typed API client, shared types, color tokens, formatting helpers
```

## Notes on the preview

- **PDF** is rendered with `react-pdf`/pdf.js; PII highlight boxes use the exact `bbox`
  coordinates the backend detector returned, scaled to the rendered page size — pixel-accurate.
- **DOCX** is converted to HTML client-side with `mammoth` (no server round-trip), then
  highlighted by matching each detection's exact text as a whole word. This is a visual
  approximation for preview purposes — the actual redaction (via `python-docx`, done in the
  backend) uses precise character offsets and is unaffected by this approximation.
- Both viewers are loaded via `next/dynamic` with `ssr: false` — `react-pdf` touches
  browser-only globals at import time and cannot be evaluated on the server.

## Deploying on Vercel

This is a standard Next.js app — Vercel auto-detects it, no `vercel.json` needed.

1. Push this repo (or just the `frontend/` directory as its own repo) and import it in Vercel.
2. Set `NEXT_PUBLIC_API_URL` (and `NEXT_PUBLIC_API_KEY` if used) as a Vercel project
   environment variable, pointing at your **publicly reachable** backend — Vercel's servers
   can't reach `localhost`.
3. On the backend, add your Vercel domain (and any preview-deployment domains) to
   `CORS_ORIGINS` in `backend/config/settings.py` / the backend's environment, or requests
   from the deployed frontend will be blocked by CORS.

## Scripts

- `npm run dev` — start the dev server (Turbopack)
- `npm run build` — production build
- `npm run start` — serve the production build
- `npm run lint` — ESLint
