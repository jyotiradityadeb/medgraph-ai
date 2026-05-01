from functools import lru_cache

from fastapi import Depends
from openai import AsyncOpenAI
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.core.embeddings import EmbeddingService
from app.core.graph_rag import GraphRAGService
from app.core.multimodal import MultiModalService
from app.db.neo4j_client import Neo4jClient, get_neo4j
from app.db.qdrant_client import QdrantService

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_qdrant_service() -> QdrantService:
    settings = get_settings()
    service = QdrantService(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    import app.db.qdrant_client as qdrant_module

    qdrant_module.qdrant_service = service
    return service


@lru_cache
def build_neo4j_client() -> Neo4jClient:
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    import app.db.neo4j_client as neo4j_module

    neo4j_module.neo4j_client = client
    return client


async def get_neo4j_service() -> Neo4jClient:
    client = await get_neo4j()
    if client is None:
        client = build_neo4j_client()
    return client


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings())


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@lru_cache
def get_multimodal_service() -> MultiModalService:
    return MultiModalService()


def get_graph_rag_service(
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    neo4j: Neo4jClient = Depends(get_neo4j_service),
) -> GraphRAGService:
    return GraphRAGService(openai_client=openai_client, neo4j_client=neo4j)
