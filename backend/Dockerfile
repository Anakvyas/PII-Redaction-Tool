FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Must match config.settings.SPACY_MODEL's default (en_core_web_md) — both
# SpacyNERDetector and PresidioDetector load that model independently (two
# full copies in one process), and only override it if SPACY_MODEL is set
# in the environment. Downloading a different model here than the app
# actually requests means every detection request 503s with
# DetectorUnavailableError at runtime, since the requested model was never
# installed.
#
# en_core_web_lg (~560MB, larger word vectors) was the original default but
# OOM-killed this app on Render's free tier: two independent full loads of
# it pushed RSS past the 512MB cap. en_core_web_md (~40MB) keeps decent NER
# quality — accuracy for PERSON/COMPANY is corroborated by regex, the
# labeled-field detector, and Presidio's own recognizers regardless of
# which spaCy model backs the NER pass — while comfortably fitting two
# loaded copies in 512MB. Upgrade to en_core_web_lg only on a host with
# more RAM headroom.
RUN pip install -r requirements.txt \
    && python -m spacy download en_core_web_md

COPY . .

RUN mkdir -p storage/files

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
