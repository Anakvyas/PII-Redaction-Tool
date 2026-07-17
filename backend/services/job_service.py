"""Job lifecycle orchestration. Request-scoped methods (create/get/review/redact)
use the session handed to them by the request; `run_detection_job` is the
background-task entry point and deliberately opens its own session, since it
keeps running after the request that scheduled it has already returned."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from core.container import get_detection_pipeline, get_storage
from core.exceptions import InvalidJobStateError, NotFoundError
from core.logging import get_logger
from models.detection import DetectionModel
from models.document import DocumentModel
from models.job import JobModel
from models.policy import PolicyModel
from replacement.pipeline import ReplacementPipeline
from schemas.common import DocumentFormat, ExtractedDocument, JobStatus, PIIEntity, PIIType, ReviewDecision, TextSpan
from schemas.detection import DetectionOut
from schemas.job import JobDetailOut, JobOut, RedactionSummaryOut
from services.extraction import get_extractor
from services.storage_service import FileStorage
from utils.ids import new_id

logger = get_logger(__name__)


class JobService:
    def __init__(self, db: Session, storage: FileStorage) -> None:
        self._db = db
        self._storage = storage

    # -- lifecycle -----------------------------------------------------
    def create(self, document_id: str, policy_id: str, pii_types: list[PIIType]) -> JobModel:
        if self._db.get(DocumentModel, document_id) is None:
            raise NotFoundError(f"Document '{document_id}' was not found.")
        if self._db.get(PolicyModel, policy_id) is None:
            raise NotFoundError(f"Policy '{policy_id}' was not found.")

        job = JobModel(
            id=new_id("job"),
            document_id=document_id,
            policy_id=policy_id,
            pii_types=[t.value for t in pii_types],
            status=JobStatus.QUEUED.value,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job

    def get(self, job_id: str) -> JobModel:
        job = self._db.get(JobModel, job_id)
        if job is None:
            raise NotFoundError(f"Job '{job_id}' was not found.")
        return job

    def list_all(self) -> list[JobModel]:
        return self._db.query(JobModel).order_by(JobModel.created_at.desc()).all()

    def review_detection(
        self, job_id: str, detection_id: str, decision: ReviewDecision, new_pii_type: PIIType | None
    ) -> DetectionModel:
        job = self.get(job_id)
        if job.status not in (JobStatus.NEEDS_REVIEW.value, JobStatus.DETECTING.value):
            raise InvalidJobStateError(
                f"Job '{job_id}' is not accepting review decisions in status '{job.status}'."
            )
        detection = self._db.get(DetectionModel, detection_id)
        if detection is None or detection.job_id != job_id:
            raise NotFoundError(f"Detection '{detection_id}' was not found on job '{job_id}'.")

        detection.human_verified = True
        detection.human_decision = decision.value
        detection.new_pii_type = new_pii_type.value if decision == ReviewDecision.RETYPE and new_pii_type else None
        self._db.commit()
        self._db.refresh(detection)
        return detection

    def redact(self, job_id: str) -> JobModel:
        job = self.get(job_id)
        if job.status != JobStatus.NEEDS_REVIEW.value:
            raise InvalidJobStateError(
                f"Job '{job_id}' must be in status 'needs_review' to redact (currently '{job.status}')."
            )
        policy = self._db.get(PolicyModel, job.policy_id)
        document = self._db.get(DocumentModel, job.document_id)

        job.status = JobStatus.REDACTING.value
        self._db.commit()

        try:
            entities = [_detection_to_entity(d) for d in job.detections]
            local_path = self._storage.path_for(document.storage_uri)
            result = ReplacementPipeline().run(
                source_path=local_path,
                document_format=DocumentFormat(document.format),
                entities=entities,
                policy_strategy_map=policy.strategy_map,
                confidence_floor=policy.confidence_floor,
            )
            key = f"redacted/{job.id}{Path(local_path).suffix}"
            job.output_storage_uri = self._storage.save_path(key, result.output_path)
            job.summary = {
                "counts_by_type": {k.value: v for k, v in result.summary.counts_by_type.items()},
                "total_redacted": result.summary.total_redacted,
            }
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.exception("Redaction failed for job %s", job_id)
            job.status = JobStatus.FAILED.value
            job.error = str(exc)
        self._db.commit()
        self._db.refresh(job)
        return job

    # -- serialization ---------------------------------------------------
    def to_out(self, job: JobModel, detailed: bool = False) -> JobOut | JobDetailOut:
        summary = RedactionSummaryOut(**job.summary) if job.summary else None
        base = dict(
            id=job.id,
            document_id=job.document_id,
            policy_id=job.policy_id,
            status=JobStatus(job.status),
            pii_types=[PIIType(t) for t in job.pii_types],
            error=job.error,
            summary=summary,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        if not detailed:
            return JobOut(**base)
        return JobDetailOut(**base, detections=[detection_to_out(d) for d in job.detections])


def detection_to_out(d: DetectionModel) -> DetectionOut:
    return DetectionOut(
        id=d.id,
        pii_type=PIIType(d.pii_type),
        span=TextSpan(
            start=d.span_start, end=d.span_end, page=d.span_page,
            bbox=tuple(d.span_bbox) if d.span_bbox else None,
        ),
        raw_value=d.raw_value,
        confidence=d.confidence,
        source_detector=d.source_detector,
        human_verified=d.human_verified,
        human_decision=ReviewDecision(d.human_decision) if d.human_decision else None,
        new_pii_type=PIIType(d.new_pii_type) if d.new_pii_type else None,
    )


def _detection_to_entity(d: DetectionModel) -> PIIEntity:
    return PIIEntity(
        id=d.id,
        pii_type=PIIType(d.pii_type),
        span=TextSpan(
            start=d.span_start, end=d.span_end, page=d.span_page,
            bbox=tuple(d.span_bbox) if d.span_bbox else None,
        ),
        raw_value=d.raw_value,
        confidence=d.confidence,
        source_detector=d.source_detector,
        human_verified=d.human_verified,
        human_decision=ReviewDecision(d.human_decision) if d.human_decision else None,
        new_pii_type=PIIType(d.new_pii_type) if d.new_pii_type else None,
    )


def run_detection_job(job_id: str) -> None:
    """Background-task entry point (scheduled via FastAPI BackgroundTasks at
    job creation). Extraction is re-derived from the stored original file
    rather than persisted, since it's a deterministic, cheap function of the
    file — that keeps the DB schema free of a large denormalized text blob."""
    from core.database import SessionLocal

    db = SessionLocal()
    storage = get_storage()
    try:
        job = db.get(JobModel, job_id)
        if job is None:
            logger.error("run_detection_job: job %s vanished before it could run", job_id)
            return

        document = db.get(DocumentModel, job.document_id)
        job.status = JobStatus.DETECTING.value
        db.commit()

        local_path = storage.path_for(document.storage_uri)
        extractor = get_extractor(DocumentFormat(document.format))
        extracted: ExtractedDocument = extractor.extract(local_path, document.id)

        requested_types = {PIIType(t) for t in job.pii_types}
        entities = get_detection_pipeline().run(extracted, requested_types)

        for entity in entities:
            db.add(
                DetectionModel(
                    id=entity.id,
                    job_id=job.id,
                    pii_type=entity.pii_type.value,
                    span_start=entity.span.start,
                    span_end=entity.span.end,
                    span_page=entity.span.page,
                    span_bbox=list(entity.span.bbox) if entity.span.bbox else None,
                    raw_value=entity.raw_value,
                    confidence=entity.confidence,
                    source_detector=entity.source_detector,
                )
            )
        job.status = JobStatus.NEEDS_REVIEW.value
        db.commit()
    except Exception as exc:  # noqa: BLE001 - background task must never raise past this point
        logger.exception("Detection failed for job %s", job_id)
        job = db.get(JobModel, job_id)
        if job is not None:
            job.status = JobStatus.FAILED.value
            job.error = str(exc)
            db.commit()
    finally:
        db.close()
