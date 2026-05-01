from __future__ import annotations

import asyncio

import structlog

import app.db.qdrant_client as qdrant_module
from app.core.embeddings import ImageEmbedder, TableEmbedder, TextEmbedder
from app.models.schemas import Source

logger = structlog.get_logger()


class MultiModalRetriever:
    def __init__(self):
        self.text_embedder = TextEmbedder()
        self.image_embedder = ImageEmbedder()
        self.table_embedder = TableEmbedder()

    async def retrieve_text(self, query: str, top_k: int = 5) -> list[Source]:
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        vector = self.text_embedder.embed(query)
        results = await qdrant_module.qdrant_service.search("medical_text", vector, top_k)
        return [
            Source(
                id=r["id"],
                content=r["payload"].get("content", ""),
                score=r["score"],
                modality="text",
                metadata=r["payload"].get("metadata", {}),
            )
            for r in results
        ]

    async def retrieve_images(self, query: str, top_k: int = 3) -> list[Source]:
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        vector = self.image_embedder.embed_text_for_image_search(query)
        results = await qdrant_module.qdrant_service.search("medical_images", vector, top_k)
        return [
            Source(
                id=r["id"],
                content=r["payload"].get("description", ""),
                score=r["score"],
                modality="image",
                metadata=r["payload"].get("metadata", {}),
            )
            for r in results
        ]

    async def retrieve_audio(self, query: str, top_k: int = 3) -> list[Source]:
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        vector = self.text_embedder.embed(query)
        results = await qdrant_module.qdrant_service.search("medical_audio", vector, top_k)
        return [
            Source(
                id=r["id"],
                content=r["payload"].get("transcript", "")[:500],
                score=r["score"],
                modality="audio",
                metadata=r["payload"].get("metadata", {}),
            )
            for r in results
        ]

    async def retrieve_tables(self, query: str, top_k: int = 3) -> list[Source]:
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        vector = self.text_embedder.embed(query)
        results = await qdrant_module.qdrant_service.search("medical_tables", vector, top_k)
        return [
            Source(
                id=r["id"],
                content=str(r["payload"].get("lab_values", {})),
                score=r["score"],
                modality="table",
                metadata={
                    **r["payload"].get("metadata", {}),
                    "abnormal_values": r["payload"].get("abnormal_values", []),
                },
            )
            for r in results
        ]

    def fuse_results_rrf(self, result_lists: list[list[Source]], k: int = 60) -> list[Source]:
        scores = {}
        docs = {}
        for results in result_lists:
            for rank, source in enumerate(results):
                sid = f"{source.modality}:{source.id}"
                if sid not in scores:
                    scores[sid] = 0.0
                    docs[sid] = source
                scores[sid] += 1.0 / (rank + k)

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        fused = []
        for sid in sorted_ids[:10]:
            doc = docs[sid]
            doc.score = round(scores[sid], 4)
            fused.append(doc)
        return fused

    async def retrieve_all_with_diagnostics(
        self,
        query: str,
        modalities: list[str] | None = None,
        top_k: int = 5,
    ) -> tuple[list[Source], list[str]]:
        modalities = modalities or ["text", "image", "audio", "table"]
        tasks = {}
        if "text" in modalities:
            tasks["text"] = self.retrieve_text(query, top_k)
        if "image" in modalities:
            tasks["image"] = self.retrieve_images(query, min(top_k, 3))
        if "audio" in modalities:
            tasks["audio"] = self.retrieve_audio(query, min(top_k, 3))
        if "table" in modalities:
            tasks["table"] = self.retrieve_tables(query, min(top_k, 3))

        results_map = {}
        failed_modalities: list[str] = []
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), gathered):
                if isinstance(result, Exception):
                    logger.warning("retrieval_failed", modality=key, error=str(result))
                    results_map[key] = []
                    failed_modalities.append(key)
                else:
                    results_map[key] = result

        all_lists = [value for value in results_map.values() if value]
        if not all_lists:
            return [], failed_modalities
        return self.fuse_results_rrf(all_lists), failed_modalities

    async def retrieve_all(
        self, query: str, modalities: list[str] | None = None, top_k: int = 5
    ) -> list[Source]:
        results, _failed_modalities = await self.retrieve_all_with_diagnostics(
            query, modalities, top_k
        )
        return results
