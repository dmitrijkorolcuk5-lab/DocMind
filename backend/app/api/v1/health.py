from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.api.dependencies import get_health_service
from app.health.service import CheckStatus, HealthService

router = APIRouter(prefix="/health", tags=["health"])
HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


class LiveResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: CheckStatus
    checks: dict[str, CheckStatus]


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    response: Response, service: HealthServiceDependency
) -> ReadyResponse:
    result = await service.check_readiness()
    if result.status == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status=result.status, checks=result.checks)
