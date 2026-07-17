from __future__ import annotations

from fastapi import APIRouter, Depends

from core.container import get_detector_registry
from detectors.registry import DetectorRegistry
from schemas.common import PIIType
from schemas.pii_type import PIITypeInfo

router = APIRouter(prefix="/pii-types", tags=["pii-types"])

_EXAMPLES: dict[PIIType, str] = {
    PIIType.PERSON: "Jane Doe",
    PIIType.EMAIL: "jane.doe@example.com",
    PIIType.PHONE: "555-123-4567",
    PIIType.COMPANY: "Initech",
    PIIType.ADDRESS: "742 Evergreen Terrace, Springfield, IL 62704",
    PIIType.SSN: "234-56-7890",
    PIIType.CREDIT_CARD: "4539 1488 0343 6467",
    PIIType.DOB: "03/14/1985",
    PIIType.IP_ADDRESS: "192.168.1.15",
}


@router.get("", response_model=list[PIITypeInfo])
async def list_pii_types(
    registry: DetectorRegistry = Depends(get_detector_registry),
) -> list[PIITypeInfo]:
    catalog = registry.catalog()
    return [
        PIITypeInfo(pii_type=t, detectors=catalog[t], example=_EXAMPLES[t]) for t in PIIType
    ]
