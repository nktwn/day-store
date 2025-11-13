from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.core.http_client import java_client
from app.routers import health, java_proxy
from app.routers import search as search_router

logger = logging.getLogger("fastapi-reco")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await java_client.ensure_service_user()
    except Exception as e:
        logger.warning("[startup] Registration attempt failed: %s", e)
    logger.info("[startup] FastAPI is up; Java base: %s", java_client.base_url)

    yield

    try:
        await java_client.aclose()
    except Exception:
        pass

app = FastAPI(
    title="FastAPI Reco Service",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(java_proxy.router)
app.include_router(search_router.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=9000, reload=True)
