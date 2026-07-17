FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Must match config.settings.SPACY_MODEL's default (en_core_web_lg) — both
# SpacyNERDetector and PresidioDetector load that model by default, and
# only override it if SPACY_MODEL is set in the environment. Downloading a
# different model here than the app actually requests means every
# detection request 503s with DetectorUnavailableError at runtime, since
# the requested model was never installed. en_core_web_lg is ~560MB vs
# en_core_web_sm's ~12MB — a real image-size cost, but accuracy (this app's
# whole job) depends on the larger model's word vectors, so it's the
# correct default; override SPACY_MODEL to en_core_web_sm only if you also
# change this download to match.
RUN pip install -r requirements.txt \
    && python -m spacy download en_core_web_lg

COPY . .

RUN mkdir -p storage/files

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
