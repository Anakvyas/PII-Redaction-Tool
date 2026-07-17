from __future__ import annotations

from fastapi import APIRouter, Depends

from api.v1.deps import get_policy_service
from schemas.policy import PolicyCreate, PolicyOut, PolicyUpdate
from services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyOut])
async def list_policies(service: PolicyService = Depends(get_policy_service)) -> list[PolicyOut]:
    return service.list()


@router.post("", response_model=PolicyOut, status_code=201)
async def create_policy(
    payload: PolicyCreate, service: PolicyService = Depends(get_policy_service)
) -> PolicyOut:
    return service.create(payload)


@router.get("/{policy_id}", response_model=PolicyOut)
async def get_policy(policy_id: str, service: PolicyService = Depends(get_policy_service)) -> PolicyOut:
    return service.get_out(policy_id)


@router.put("/{policy_id}", response_model=PolicyOut)
async def update_policy(
    policy_id: str, payload: PolicyUpdate, service: PolicyService = Depends(get_policy_service)
) -> PolicyOut:
    return service.update(policy_id, payload)
