"""FastAPI app entry point.

Run from the project root:
    uvicorn backend.main:app --reload
Docs: http://127.0.0.1:8000/docs     API base: http://127.0.0.1:8000/api/v1

Other computers on the office network (listen on all interfaces):
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
HTTPS (see README "Running with HTTPS"):
    uvicorn backend.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem

Layers (each only talks to the one below it):
    routers/       HTTP only: read the request, call a service, return the response
    services/      business rules (no HTTP, no SQL)
    repositories/  database queries
    models.py      tables (schema changes: Alembic, see backend/migrations)
"""
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from .core import database, i18n
from .core.config import config
from .core.database import SessionLocal
from .core.errors import DomainError, Unauthorized
from .core.logging import get_logger, setup_logging
from .core.migrations import upgrade_database
from .routers import attendance, auth, dashboard, departments, employees, leaves, payroll, requisitions, settings, users
from .schemas import Health
from .seed import seed_if_empty

VERSION = "1.3.0"
setup_logging()
log = get_logger("app")
access_log = get_logger("access")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    upgrade_database()
    with SessionLocal() as db:
        if seed_if_empty(db):
            log.info("Database was empty - demo data loaded (admin/admin123, hr/hr123, employee/emp123)")
    log.info("HRMS API %s ready (API base %s)", VERSION, config.api_prefix)
    yield


app = FastAPI(title="HRMS API", version=VERSION, lifespan=lifespan,
              description="REST API for the HR Management System desktop app. "
                          f"All endpoints are under `{config.api_prefix}`.")


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Pick the response language, then log one line per request (never the body or token)."""
    i18n.set_language(i18n.parse_accept_language(request.headers.get("accept-language")))
    start = time.perf_counter()
    response = await call_next(request)
    access_log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    """Services raise domain errors; this is the one place they become HTTP responses."""
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, Unauthorized) else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Same 422 body as FastAPI's default, with our own validation messages translated."""
    errors = []
    for err in exc.errors():
        err = {k: v for k, v in err.items() if k in ("loc", "msg", "type")}
        msg = str(err.get("msg", ""))
        if msg.startswith("Value error, "):
            err["msg"] = "Value error, " + i18n.gettext_(msg[len("Value error, "):])
        errors.append(err)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


api = APIRouter(prefix=config.api_prefix)
for module in (auth, employees, departments, attendance, leaves, payroll, dashboard, settings, users,
               requisitions):
    api.include_router(module.router)
app.include_router(api)


@app.get("/", response_model=Health, tags=["Health"])
def health() -> dict:
    """Liveness and database check (no login needed; used by the desktop app and monitoring)."""
    db_ok = database.ping()
    body = {"status": "ok" if db_ok else "degraded", "service": "HRMS API", "version": VERSION,
            "database": "ok" if db_ok else "unreachable"}
    return JSONResponse(body, status_code=200 if db_ok else 503)
