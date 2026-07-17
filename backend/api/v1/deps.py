"""FastAPI dependency providers — the app's dependency-injection wiring.
Request-scoped services are constructed here from a request-scoped DB session
plus the stateless singletons in core.container; nothing imports a concrete
adapter directly outside of this file and core/container.py."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from config.settings import Settings, get_settings
from core.container import get_storage
from core.database import get_db
from services.document_service import DocumentService
from services.job_service import JobService
from services.policy_service import PolicyService
from services.storage_service import FileStorage


def get_document_service(
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(db=db, storage=storage, settings=settings)


def get_job_service(
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> JobService:
    return JobService(db=db, storage=storage)


def get_policy_service(db: Session = Depends(get_db)) -> PolicyService:
    return PolicyService(db=db)
