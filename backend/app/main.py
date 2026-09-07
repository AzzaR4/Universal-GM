"""FastAPI application entrypoint for the Universal AI Game Master."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    actions,
    campaigns,
    characters,
    export,
    locations,
    npcs,
    settings as settings_api,
    stream,
)
from app.config import settings
from app.core.exceptions import DomainError
from app.db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


# Router registration.
app.include_router(campaigns.meta_router)
app.include_router(campaigns.router)
app.include_router(characters.router)
app.include_router(npcs.router)
app.include_router(locations.router)
app.include_router(actions.router)
app.include_router(stream.router)
app.include_router(settings_api.router)
app.include_router(export.router)
