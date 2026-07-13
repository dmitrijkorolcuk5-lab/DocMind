import asyncio
from dataclasses import dataclass
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.storage.base import HealthCheckableObjectStorage

CheckStatus = Literal["ok", "error"]


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    status: CheckStatus
    checks: dict[str, CheckStatus]


class HealthService:
    def __init__(
        self,
        engine: AsyncEngine,
        redis: Redis,
        storage: HealthCheckableObjectStorage,
    ) -> None:
        self._engine = engine
        self._redis = redis
        self._storage = storage

    async def _database_ready(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def _redis_ready(self) -> None:
        await self._redis.ping()

    async def check_readiness(self) -> ReadinessResult:
        results = await asyncio.gather(
            self._database_ready(),
            self._redis_ready(),
            self._storage.healthcheck(),
            return_exceptions=True,
        )
        names = ("database", "redis", "object_storage")
        checks: dict[str, CheckStatus] = {
            name: "error" if isinstance(result, BaseException) else "ok"
            for name, result in zip(names, results, strict=True)
        }
        return ReadinessResult(
            status="ok" if all(value == "ok" for value in checks.values()) else "error",
            checks=checks,
        )

