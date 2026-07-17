from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from schemas.common import PIIType


class EvaluationMetricsOut(BaseModel):
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


class EvaluationRunCreate(BaseModel):
    dataset: str = "bundled_sample"  # only the bundled synthetic gold set is supported today


class EvaluationRunOut(BaseModel):
    id: str
    dataset_id: str
    detector_version: str
    overall: EvaluationMetricsOut
    per_type: dict[PIIType, EvaluationMetricsOut]
    started_at: datetime
    completed_at: datetime

    model_config = {"from_attributes": True}
