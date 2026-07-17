"""Import every mapped model so Base.metadata is fully populated before
`Base.metadata.create_all()` runs in core.database.init_db()."""
from models.document import DocumentModel
from models.policy import PolicyModel
from models.job import JobModel
from models.detection import DetectionModel
from models.evaluation import EvaluationRunModel
from models.audit_log import AuditLogModel

__all__ = [
    "DocumentModel",
    "PolicyModel",
    "JobModel",
    "DetectionModel",
    "EvaluationRunModel",
    "AuditLogModel",
]
