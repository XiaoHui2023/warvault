from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app_main.api import router as api_router
from app_main.auto_refresh import auto_refresh_loop
from app_main.config import load_config, set_config_path

logger = logging.getLogger(__name__)


def create_app(config_path: str | None = None) -> FastAPI:
    if config_path is not None:
        set_config_path(config_path)

    app_config = load_config(config_path)
    base_url = app_config.server.base_url

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task: asyncio.Task | None = None
        if app_config.auto_refresh.enabled:
            task = asyncio.create_task(auto_refresh_loop(app_config.auto_refresh))
            logger.info(
                "Auto refresh enabled interval_seconds=%s initial_scan=%s",
                app_config.auto_refresh.interval_seconds,
                app_config.auto_refresh.initial_scan,
            )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="warvault", version="0.0.0", lifespan=lifespan)
    app.include_router(api_router, prefix=_router_prefix(base_url))

    dist = app_config.paths.frontend_dist
    assets = dist / "assets"
    if assets.is_dir():
        app.mount(_join_base(base_url, "/assets"), StaticFiles(directory=assets), name="assets")

    if base_url != "/":
        @app.get(base_url, include_in_schema=False)
        async def base_redirect():
            return RedirectResponse(f"{base_url}/")

    @app.get(_join_base(base_url, "/{full_path:path}"), include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "API route not found"}, status_code=404)

        if not dist.is_dir():
            return JSONResponse(
                {
                    "detail": "Frontend has not been built. Run npm install and npm run build in frontend/.",
                },
                status_code=503,
            )

        requested = dist / full_path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(dist / "index.html")

    return app


def _router_prefix(base_url: str) -> str:
    return "" if base_url == "/" else base_url


def _join_base(base_url: str, path: str) -> str:
    if base_url == "/":
        return path
    return f"{base_url}{path}"
