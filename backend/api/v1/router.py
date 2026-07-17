"""Versioned API root. A future v2 would be a sibling package mounted at a
different prefix in main.py — nothing about this wiring is v1-specific."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.v1 import documents, evaluation, files, jobs, pii_types, policies
from core.security import require_api_key

router = APIRouter()
router.include_router(documents.router, dependencies=[Depends(require_api_key)])
router.include_router(jobs.router, dependencies=[Depends(require_api_key)])
router.include_router(policies.router, dependencies=[Depends(require_api_key)])
router.include_router(pii_types.router, dependencies=[Depends(require_api_key)])
router.include_router(evaluation.router, dependencies=[Depends(require_api_key)])
router.include_router(files.router)  # signed-token auth, not the API key
