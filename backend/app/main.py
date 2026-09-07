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
    combat,
    export,
    locations,
    memories,
    npcs,
    party,
    rulesets_api,
    scenes,
    sessions_api,
    settings as settings_api,
    stream,
    world,
)
from app.config import settings
from app.core.exceptions import DomainError
from app.db.base import SessionLocal, init_db
from app.rulesets import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Load any DB-stored custom rulesets into the live registry.
    try:
        async with SessionLocal() as session:
            await registry.load_custom_rulesets(session)
    except Exception:  # noqa: BLE001 - never block startup on custom ruleset load
        pass
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
app.include_router(combat.router)
app.include_router(scenes.router)
app.include_router(stream.router)
app.include_router(settings_api.router)
app.include_router(export.router)
# Session 3 routers.
app.include_router(party.router)
app.include_router(party.schema_router)
app.include_router(world.router)
app.include_router(memories.router)
app.include_router(sessions_api.router)
app.include_router(rulesets_api.router)
