"""App wiring: config/db bootstrap happens at import time (SessionMiddleware
needs the session secret before the app is constructed), then routers,
static frontend serving, and the startup/shutdown lifecycle for the shared
Netris HTTP client and background task manager.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app import db, seed, settings_store
from app.config import load_config
from app.netris.client import NetrisClient
from app.ops.router import router as ops_router
from app.routers.auth import router as auth_router
from app.routers.environments import router as environments_router
from app.security import SecretBox
from app.worker import BackgroundTaskManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")

CFG = load_config()
db.init_db(CFG.db_path)
settings_store.ensure_bootstrapped(CFG)
SECRET_BOX = SecretBox(CFG.fernet_key)
_settings = settings_store.get_settings()

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="HeliosGrid Provider Portal", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=_settings.session_secret, same_site="lax")

app.state.secret_box = SECRET_BOX

app.include_router(auth_router)
app.include_router(environments_router)
app.include_router(ops_router)


@app.on_event("startup")
async def on_startup() -> None:
    settings = settings_store.get_settings()
    http_client = httpx.AsyncClient(verify=bool(settings.netris_verify_ssl))
    app.state.http_client = http_client
    app.state.netris_client = NetrisClient(http_client, SECRET_BOX)
    app.state.task_manager = BackgroundTaskManager(app.state.netris_client, SECRET_BOX)

    seed.seed_dummy_environments()
    app.state.task_manager.resume_all_incomplete()
    logger.info("Startup complete (Netris configured: %s)", settings.netris_configured)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await app.state.http_client.aclose()
    db.close_db()


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/{full_path:path}")
async def spa_catch_all(full_path: str):
    if full_path.startswith("api/") or full_path == "api" or full_path.startswith("ops"):
        raise HTTPException(status_code=404)
    if not FRONTEND_DIST.exists():
        raise HTTPException(status_code=503, detail="Frontend not built yet — run `npm run build` in frontend/.")
    candidate = FRONTEND_DIST / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIST / "index.html")
