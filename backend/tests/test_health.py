from typing import cast

import httpx
from fastapi import FastAPI

from app.api.dependencies import get_health_service
from app.health.service import HealthService, ReadinessResult


class FakeHealthService:
    def __init__(self, result: ReadinessResult) -> None:
        self._result = result

    async def check_readiness(self) -> ReadinessResult:
        return self._result


async def test_health_live(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_health_ready_success(app: FastAPI, client: httpx.AsyncClient) -> None:
    service = FakeHealthService(
        ReadinessResult(
            status="ok", checks={"database": "ok", "redis": "ok", "object_storage": "ok"}
        )
    )
    app.dependency_overrides[get_health_service] = lambda: cast(HealthService, service)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {
        "database": "ok",
        "redis": "ok",
        "object_storage": "ok",
    }


async def test_health_ready_failure(app: FastAPI, client: httpx.AsyncClient) -> None:
    service = FakeHealthService(
        ReadinessResult(
            status="error",
            checks={"database": "ok", "redis": "error", "object_storage": "ok"},
        )
    )
    app.dependency_overrides[get_health_service] = lambda: cast(HealthService, service)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "error"

