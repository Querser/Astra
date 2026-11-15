"""Entrypoint for the ASTRA local demonstration API."""

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api import router
from app.assistant import LocalAssistant
from app.smart_chat import LocalChatModel
from app.config import get_settings
from app.db import Database, sqlite_url, upgrade_database
from app.diagnostics import configure_logger
from app.research_data import import_packaged_snapshots, router as research_router
from app.security import ALLOWED_BROWSER_ORIGINS, LocalRequestGuard
from app.single_profile import ensure_single_profile


class HealthResponse(BaseModel):
    """Non-clinical status response for local setup checks."""

    service: str
    status: str
    stage: int
    data_dir: str
    clinical_analysis_available: bool


def create_app(
    database_url: str | None = None,
    log_dir: Path | None = None,
    automated_ingestion_enabled: bool | None = None,
    chat_model_enabled: bool | None = None,
    browser_origins: set[str] | None = None,
    seed_default_profile: bool = False,
) -> FastAPI:
    """Construct a local API instance and apply migrations when it starts."""

    settings = get_settings()
    resolved_database_url = database_url or settings.database_url or sqlite_url(settings.data_dir / "astra.sqlite3")
    resolved_log_dir = log_dir or settings.data_dir / "logs"
    allowed_origins = browser_origins if browser_origins is not None else ALLOWED_BROWSER_ORIGINS

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        upgrade_database(resolved_database_url)
        application.state.diagnostics = configure_logger(resolved_log_dir)
        with application.state.database.session_factory() as session:
            import_counts = import_packaged_snapshots(session)
            if seed_default_profile:
                ensure_single_profile(session)
        application.state.diagnostics.info("research_snapshots_ready", extra=import_counts)
        application.state.diagnostics.info("service_start")
        try:
            yield
        finally:
            application.state.diagnostics.info("service_stop")
            application.state.database.dispose()
            for handler in application.state.diagnostics.handlers[:]:
                application.state.diagnostics.removeHandler(handler)
                handler.close()

    application = FastAPI(
        title="ASTRA Local API",
        version="0.2.0",
        description=(
            "Local fictional-data record service with source-linked educational "
            "comparisons. It does not provide validated clinical conclusions."
        ),
        lifespan=lifespan,
    )
    application.state.database = Database(resolved_database_url)
    application.state.local_assistant = LocalAssistant()
    application.state.chat_model = LocalChatModel(enabled=chat_model_enabled)
    application.state.automated_ingestion_enabled = (
        settings.automated_ingestion_enabled
        if automated_ingestion_enabled is None
        else automated_ingestion_enabled
    )

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = str(uuid4())
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as error:
            diagnostics = getattr(application.state, "diagnostics", None)
            if diagnostics is not None:
                diagnostics.error(
                    "request_exception",
                    extra={"request_id": request_id, "error_type": type(error).__name__},
                )
            raise
        finally:
            diagnostics = getattr(application.state, "diagnostics", None)
            if diagnostics is not None:
                route = request.scope.get("route")
                diagnostics.info(
                    "http_request",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "route": getattr(route, "path", "unmatched"),
                        "status": status_code,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                    },
                )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.add_middleware(LocalRequestGuard, allowed_origins=allowed_origins)

    @application.get(f"{settings.api_prefix}/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            service="astra-api",
            status="ready",
            stage=13,
            data_dir=str(settings.data_dir),
            clinical_analysis_available=False,
        )

    application.include_router(router, prefix=settings.api_prefix)
    application.include_router(research_router, prefix=settings.api_prefix)
    return application


app = create_app(seed_default_profile=True)
