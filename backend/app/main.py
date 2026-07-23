import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
import app.models  # noqa: F401 — register all ORM models with SQLAlchemy
from app.providers.impl.qdrant_store import get_vector_store
from app.routes import auth, documents, projects, users
from app.services.rag_warmup import warmup_rag_models
from app.utils.http_client import close_async_http_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chatbot Platform API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(documents.router)


@app.on_event("startup")
async def startup_event():
    if settings.rag_enabled:
        await get_vector_store().ensure_collection()
        asyncio.create_task(warmup_rag_models())


@app.on_event("shutdown")
async def shutdown_event():
    await close_async_http_client()


@app.get("/health")
def health_check():
    return {"status": "ok"}
