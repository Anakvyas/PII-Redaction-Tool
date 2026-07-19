---
title: PII Redaction API
emoji: 🔒
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# PII Redaction API (Hugging Face Space)

FastAPI backend for the PII Redaction Tool, deployed here as a Docker Space
to get more headroom than Render's free tier (512MB RAM / 0.1 CPU) —
this tier gives 2 vCPU / 16GB RAM.

This `README.md`'s YAML frontmatter is what tells Spaces to build the
`Dockerfile` in this folder and route traffic to port 8000 (the port
`uvicorn` binds to in the Dockerfile — unchanged from the Render deploy).

## Required Space secrets

Set these under Space settings → *Variables and secrets* before the first
real request (all have insecure/empty local-dev defaults otherwise):

| Name | Value |
| --- | --- |
| `API_KEY` | a real key — empty disables auth entirely |
| `SECRET_KEY` | random secret — signs download tokens |
| `CORS_ORIGINS` | `["https://pii-redaction-tool-livid.vercel.app"]` (or a comma-separated list) |

## Storage caveat

`STORAGE_BACKEND=local` (the default) writes uploaded/redacted files to
`storage/files/` and job records to a SQLite file at `storage/pii_redactor.db`,
both on local disk. **Spaces' free-tier disk is ephemeral** — it resets on
every restart (Space sleep/wake, or a new push), so job history and any
files older than the current running instance are wiped. Given
`SIGNED_URL_TTL_SECONDS=900` (download links expire after 15 min anyway),
this is usually fine for redact-and-download use — but the **jobs list**
(`/workspace/jobs`) won't survive a restart. If persistent history matters,
switch `STORAGE_BACKEND=s3` (already supported in `config/settings.py`) and
point `DATABASE_URL` at an external Postgres instance instead of SQLite.

## SPACY_MODEL note

The Dockerfile only downloads `en_core_web_md` at build time (Render's
512MB forced that — see the comment in `Dockerfile`). With 16GB available
here you could upgrade to `en_core_web_lg` for better NER accuracy, but
that requires changing the `python -m spacy download` line in the
Dockerfile too — setting the `SPACY_MODEL` env var alone isn't enough,
the larger model needs to actually be installed in the image.

## Deploying

From the repo root:

```bash
# one-time: create the Space on huggingface.co (Docker SDK), then:
git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
git subtree push --prefix backend space main
```

Re-run the `git subtree push` command after each change to ship it.
