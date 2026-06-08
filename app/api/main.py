from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

from app.factory.yaml_loader import load_agents_from_dir
from app.internal.config import get_settings
from app.internal.logging import configure_logging, logger
from app.internal.shutdown import is_shutting_down, lifespan_signals
from app.storage.sqlite import close_db, init_db
from app.storage.templates import list_templates as _list_templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    logger.info("startup.begin", db=str(settings.database_path))

    async with lifespan_signals():
        await init_db()
        await load_agents_from_dir(settings.agents_dir)
        logger.info("startup.complete")
        try:
            yield
        finally:
            logger.info("shutdown.begin")
            await close_db()
            logger.info("shutdown.complete")


app = FastAPI(title="newagentic", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if is_shutting_down():
        raise HTTPException(status_code=503, detail="shutting down")
    return {"status": "ready"}


@app.get("/templates")
async def list_templates() -> list[dict[str, object]]:
    return await _list_templates()
