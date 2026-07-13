from typing import ClassVar

from arq.connections import RedisSettings
from arq.cron import CronJob, cron

from app.core.config import get_settings
from app.workers.tasks import health_job, process_document, recover_stale_documents

settings = get_settings()


class WorkerSettings:
    functions: ClassVar[list[object]] = [health_job, process_document]
    redis_settings: ClassVar[RedisSettings] = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DATABASE,
    )
    queue_name: ClassVar[str] = settings.ARQ_QUEUE_NAME
    cron_jobs: ClassVar[list[CronJob]] = [
        cron(
            recover_stale_documents,
            minute=set(range(60)),
            run_at_startup=True,
            timeout=settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS,
        )
    ]
    max_jobs: ClassVar[int] = 10
    job_timeout: ClassVar[int] = settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS
    max_tries: ClassVar[int] = 1
    health_check_interval: ClassVar[int] = 30
