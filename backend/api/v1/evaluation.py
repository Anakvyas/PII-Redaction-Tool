from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.exceptions import NotFoundError
from evaluation.pipeline import DETECTOR_VERSION, EvaluationPipeline
from models.evaluation import EvaluationRunModel
from schemas.common import PIIType
from schemas.evaluation import EvaluationMetricsOut, EvaluationRunCreate, EvaluationRunOut
from utils.ids import new_id

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/runs", response_model=EvaluationRunOut, status_code=201)
async def create_evaluation_run(
    payload: EvaluationRunCreate, db: Session = Depends(get_db)
) -> EvaluationRunOut:
    started = datetime.now(timezone.utc)
    overall, per_type = EvaluationPipeline().run()
    completed = datetime.now(timezone.utc)

    record = EvaluationRunModel(
        id=new_id("eval"),
        dataset_id=payload.dataset,
        detector_version=DETECTOR_VERSION,
        metrics={
            "overall": overall.__dict__,
            "per_type": {k.value: v.__dict__ for k, v in per_type.items()},
        },
        started_at=started,
        completed_at=completed,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record)


@router.get("/runs/{run_id}", response_model=EvaluationRunOut)
async def get_evaluation_run(run_id: str, db: Session = Depends(get_db)) -> EvaluationRunOut:
    record = db.get(EvaluationRunModel, run_id)
    if record is None:
        raise NotFoundError(f"Evaluation run '{run_id}' was not found.")
    return _to_out(record)


def _to_out(record: EvaluationRunModel) -> EvaluationRunOut:
    return EvaluationRunOut(
        id=record.id,
        dataset_id=record.dataset_id,
        detector_version=record.detector_version,
        overall=EvaluationMetricsOut(**record.metrics["overall"]),
        per_type={
            PIIType(k): EvaluationMetricsOut(**v) for k, v in record.metrics["per_type"].items()
        },
        started_at=record.started_at,
        completed_at=record.completed_at,
    )
