"""Job endpoints. Detection runs as a background task scheduled at job
creation; redaction runs synchronously inside the POST /redact request since
it only replays already-approved detections (fast, no model inference)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from api.v1.deps import get_job_service
from config.settings import get_settings
from core.container import get_storage
from core.database import SessionLocal
from core.exceptions import InvalidJobStateError
from models.job import JobModel
from schemas.common import JobStatus
from schemas.detection import DetectionOut, DetectionReviewUpdate
from schemas.job import DownloadOut, JobCreate, JobDetailOut, JobOut
from services.job_service import JobService, detection_to_out, run_detection_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(get_job_service),
) -> JobOut:
    job = service.create(payload.document_id, payload.policy_id, payload.pii_types)
    background_tasks.add_task(run_detection_job, job.id)
    return service.to_out(job)


@router.get("/{job_id}", response_model=JobDetailOut)
async def get_job(job_id: str, service: JobService = Depends(get_job_service)) -> JobDetailOut:
    return service.to_out(service.get(job_id), detailed=True)


@router.get("/{job_id}/detections", response_model=list[DetectionOut])
async def list_detections(
    job_id: str, service: JobService = Depends(get_job_service)
) -> list[DetectionOut]:
    detail: JobDetailOut = service.to_out(service.get(job_id), detailed=True)
    return detail.detections


@router.patch("/{job_id}/detections/{detection_id}", response_model=DetectionOut)
async def review_detection(
    job_id: str,
    detection_id: str,
    payload: DetectionReviewUpdate,
    service: JobService = Depends(get_job_service),
) -> DetectionOut:
    detection = service.review_detection(job_id, detection_id, payload.decision, payload.new_pii_type)
    return detection_to_out(detection)


@router.post("/{job_id}/redact", response_model=JobOut)
async def redact_job(job_id: str, service: JobService = Depends(get_job_service)) -> JobOut:
    job = service.redact(job_id)
    return service.to_out(job)


@router.get("/{job_id}/download", response_model=DownloadOut)
async def download_job(job_id: str, service: JobService = Depends(get_job_service)) -> DownloadOut:
    job = service.get(job_id)
    if job.status != JobStatus.COMPLETED.value or not job.output_storage_uri:
        raise InvalidJobStateError(
            f"Job '{job_id}' has no redacted file yet (status '{job.status}')."
        )
    settings = get_settings()
    url = get_storage().signed_url(job.output_storage_uri, expires_in=settings.SIGNED_URL_TTL_SECONDS)
    return DownloadOut(url=url, expires_in=settings.SIGNED_URL_TTL_SECONDS)


@router.get("/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    async def event_source():
        last_status: str | None = None
        for _ in range(600):  # ~10 minutes of polling; the client reconnects if still open
            db = SessionLocal()
            try:
                job = db.get(JobModel, job_id)
                if job is None:
                    yield f"event: error\ndata: {json.dumps({'message': 'job not found'})}\n\n"
                    return
                if job.status != last_status:
                    last_status = job.status
                    yield f"data: {json.dumps({'status': job.status, 'error': job.error})}\n\n"
                if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                    return
            finally:
                db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_source(), media_type="text/event-stream")
