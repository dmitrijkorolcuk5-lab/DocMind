from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import health_job

settings = get_settings()


class WorkerSettings:
    functions: ClassVar[list[object]] = [health_job]
    redis_settings: ClassVar[RedisSettings] = RedisSettings(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT
    )
    max_jobs: ClassVar[int] = 10
    job_timeout: ClassVar[int] = 60
    health_check_interval: ClassVar[int] = 30
