from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.api.deps import build_neo4j_client, get_neo4j_service, get_qdrant_service, limiter
from app.api.routes.graph import router as graph_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.query import router as query_router
from app.config import get_settings
from app.utils.error_handlers import (
    MedGraphException,
    generic_exception_handler,
    medgraph_exception_handler,
    validation_exception_handler,
)
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    qdrant = get_qdrant_service()
    neo4j = build_neo4j_client()

    qdrant_ok = False
    neo4j_ok = False

    try:
        await qdrant.initialize()
        qdrant_ok = await qdrant.verify_connectivity()
    except Exception as exc:
        logger.error("startup.qdrant.failed", error=str(exc))

    try:
        await neo4j.create_schema()
        neo4j_ok = await neo4j.verify_connectivity()
    except Exception as exc:
        logger.error("startup.neo4j.failed", error=str(exc))

    app.state.qdrant_ready = qdrant_ok
    app.state.neo4j_ready = neo4j_ok
    logger.info("startup.ready", qdrant=qdrant_ok, neo4j=neo4j_ok, environment=settings.APP_ENV)

    yield

    try:
        await neo4j.close()
    except Exception as exc:
        logger.warning("shutdown.neo4j.close.failed", error=str(exc))


app = FastAPI(title="MedGraph AI API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(MedGraphException, medgraph_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/api/v1/query")
app.include_router(ingest_router, prefix="/api/v1/ingest")
app.include_router(graph_router, prefix="/api/v1/graph")
app.include_router(metrics_router, prefix="/api/v1/metrics")


@app.get("/health")
async def health():
    qdrant_service = get_qdrant_service()
    neo4j_service = await get_neo4j_service()

    qdrant_ok = await qdrant_service.verify_connectivity()
    neo4j_ok = await neo4j_service.verify_connectivity()

    return {
        "status": "ok",
        "services": {"qdrant": qdrant_ok, "neo4j": neo4j_ok},
        "version": "1.0.0",
    }
