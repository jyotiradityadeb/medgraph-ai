from __future__ import annotations

import uuid
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = structlog.get_logger()

COLLECTIONS = {
    "medical_text": {"size": 384, "distance": Distance.COSINE},
    "medical_images": {"size": 512, "distance": Distance.COSINE},
    "medical_audio": {"size": 384, "distance": Distance.COSINE},
    "medical_tables": {"size": 384, "distance": Distance.COSINE},
}


class QdrantService:
    def __init__(self, host: str, port: int):
        self.client = AsyncQdrantClient(host=host, port=port)

    async def initialize(self):
        existing = await self.client.get_collections()
        existing_names = [c.name for c in existing.collections]
        for name, config in COLLECTIONS.items():
            if name not in existing_names:
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=config["size"], distance=config["distance"]),
                )
                logger.info("collection_created", name=name)

    async def upsert(
        self,
        collection: str,
        vector: list[float],
        payload: dict[str, Any],
        point_id: str | None = None,
    ) -> str:
        pid = point_id or str(uuid.uuid4())
        await self.client.upsert(
            collection_name=collection, points=[PointStruct(id=pid, vector=vector, payload=payload)]
        )
        return pid

    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_dict.items()
            ]
            query_filter = Filter(must=conditions)

        results = await self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            {"id": str(r.id), "score": float(r.score), "payload": r.payload or {}} for r in results
        ]

    async def get_collection_info(self, name: str) -> dict[str, Any]:
        info = await self.client.get_collection(name)
        return {"name": name, "points_count": info.points_count, "status": str(info.status)}

    async def verify_connectivity(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False


qdrant_service: QdrantService = None
