import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import check_database
import app.models  # noqa: F401 — register all ORM models with SQLAlchemy
from app.observability import metrics, setup_tracing
from app.providers.impl.qdrant_store import get_vector_store
from app.routes import auth, documents, exports, models, projects, users
from app.services.rag_warmup import warmup_rag_models
from app.utils.http_client import close_async_http_client, get_async_http_client
from app.utils.exception_handlers import register_exception_handlers
from app.utils.rate_limit import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="YelloBot API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path


MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "XMLHttpRequest"
CSRF_EXEMPT_PREFIXES = ("/health", "/metrics")


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if settings.is_production and request.method in MUTATING_METHODS:
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES):
            if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )
    return await call_next(request)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        if settings.metrics_enabled:
            path = _route_template(request)
            metrics.HTTP_REQUESTS.labels(
                method=request.method, path=path, status="500"
            ).inc()
            metrics.HTTP_REQUEST_DURATION.labels(
                method=request.method, path=path
            ).observe(time.perf_counter() - started)
        raise

    elapsed = time.perf_counter() - started
    path = _route_template(request)
    if settings.metrics_enabled and path != "/metrics":
        metrics.HTTP_REQUESTS.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        metrics.HTTP_REQUEST_DURATION.labels(method=request.method, path=path).observe(elapsed)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(models.router)
app.include_router(projects.router)
app.include_router(exports.router)
app.include_router(documents.router)


@app.on_event("startup")
async def startup_event():
    if settings.metrics_enabled:
        metrics.init_service_info(environment=settings.environment)
    setup_tracing()

    if settings.rag_enabled:
        try:
            await asyncio.wait_for(get_vector_store().ensure_collection(), timeout=5.0)
        except Exception:
            logger.warning(
                "Qdrant unavailable at startup — API will still start; RAG retries on first use"
            )
        asyncio.create_task(warmup_rag_models())


@app.on_event("shutdown")
async def shutdown_event():
    await close_async_http_client()


async def _check_redis() -> bool:
    try:
        from redis.asyncio import from_url

        client = from_url(settings.redis_url, socket_connect_timeout=1.5)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False


async def _check_qdrant() -> bool:
    if not settings.rag_enabled:
        return True
    try:
        client = get_async_http_client()
        response = await client.get(f"{settings.qdrant_url.rstrip('/')}/readyz", timeout=2.0)
        return response.status_code < 500
    except Exception:
        return False


@app.get("/health")
async def health_check():
    checks = {
        "database": check_database(),
        "redis": await _check_redis(),
        "qdrant": await _check_qdrant(),
    }
    if not settings.ingestion_inline_fallback and not checks["redis"]:
        healthy = False
    else:
        healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "degraded",
            "checks": checks,
            "ingestion_inline_fallback": settings.ingestion_inline_fallback,
        },
    )


@app.get("/metrics")
async def prometheus_metrics(request: Request):
    if not settings.metrics_enabled:
        return Response(status_code=404)
    if settings.is_production:
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else auth
        if token != settings.metrics_token:
            return Response(status_code=401)
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
