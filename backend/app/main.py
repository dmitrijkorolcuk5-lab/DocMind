from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from arq.connections import RedisSettings, create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.database.session import engine
from app.storage.minio import MinioObjectStorage, StorageError

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    arq_redis = await create_pool(
        RedisSettings(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            database=settings.REDIS_DATABASE,
        ),
        default_queue_name=settings.ARQ_QUEUE_NAME,
    )
    storage = MinioObjectStorage(settings)
    app.state.redis = redis
    app.state.arq_redis = arq_redis
    app.state.object_storage = storage
    try:
        await storage.ensure_bucket()
    except StorageError:
        logger.warning("object_storage_initialization_failed", exc_info=True)
    try:
        yield
    finally:
        await arq_redis.aclose()
        await redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    register_exception_handlers(application)
    return application


app = create_app()
