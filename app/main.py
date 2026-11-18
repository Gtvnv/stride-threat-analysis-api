"""Ponto de entrada: ``uvicorn app.main:app``."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.errors import register_exception_handlers
from app.api.routes import router
from app.core.logging import (
    Timer,
    configure_logging,
    log_event,
    reset_request_id,
    set_request_id,
)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="STRIDE Threat Analysis API", version="1.0.0")
    register_exception_handlers(app)
    app.include_router(router)

    @app.middleware("http")
    async def request_logging(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = set_request_id()
        timer = Timer()
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                "request_failed",
                level=logging.ERROR,
                duration_ms=timer.elapsed_ms(),
                exception_type=type(exc).__name__,
                method=request.method,
                path=request.url.path,
            )
            raise
        else:
            log_event(
                "request_completed",
                duration_ms=timer.elapsed_ms(),
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
            )
            return response
        finally:
            reset_request_id(token)

    return app


app = create_app()
