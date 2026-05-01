from __future__ import annotations

import re
import uuid
from typing import Any

import structlog

import app.db.neo4j_client as neo4j_module
import app.db.qdrant_client as qdrant_module
from app.core.embeddings import AudioTranscriber, ImageEmbedder, TableEmbedder, TextEmbedder

logger = structlog.get_logger()


class MultiModalService:
    def __init__(self):
        self._entity_pattern = re.compile(r"\b[A-Z][a-zA-Z0-9\-]{2,}\b")
        self._medical_terms = {
            "diabetes",
            "hypertension",
            "ckd",
            "copd",
            "asthma",
            "warfarin",
            "insulin",
            "metformin",
            "creatinine",
            "troponin",
            "d-dimer",
        }

    def extract_entities(self, content: str) -> list[str]:
        tokens = set(match.group(0) for match in self._entity_pattern.finditer(content))
        lowered = content.lower()
        for term in self._medical_terms:
            if term in lowered:
                tokens.add(term.title())
        return sorted(tokens)[:25]

    def detect_modalities(self, query: str, requested_modalities: list[str]) -> list[str]:
        query_lower = query.lower()
        modalities = set(requested_modalities or ["text"])
        if any(
            word in query_lower for word in ["image", "xray", "ct", "mri", "scan", "ultrasound"]
        ):
            modalities.add("image")
        if any(word in query_lower for word in ["audio", "voice", "dictation"]):
            modalities.add("audio")
        if any(word in query_lower for word in ["lab", "table", "panel", "values"]):
            modalities.add("table")
        if any(word in query_lower for word in ["pdf", "paper", "guideline", "document"]):
            modalities.add("document")
        return sorted(modalities)


class MultiModalIngestPipeline:
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.text_embedder = TextEmbedder()
        self.image_embedder = ImageEmbedder()
        self.audio_transcriber = AudioTranscriber(openai_client)
        self.table_embedder = TableEmbedder()
        self.entity_service = MultiModalService()

    async def ingest_text(
        self, text: str, source: str = "", metadata: dict[str, Any] | None = None
    ) -> tuple[str, list[str]]:
        metadata = metadata or {}
        chunks = self.text_embedder.chunk_text(text)
        doc_id = str(uuid.uuid4())
        entities_found = self.entity_service.extract_entities(text)

        for i, chunk in enumerate(chunks):
            vector = self.text_embedder.embed(chunk)
            payload = {
                "content": chunk,
                "source": source,
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "modality": "text",
                "metadata": metadata,
            }
            if qdrant_module.qdrant_service is None:
                raise RuntimeError("Qdrant service is not initialized.")
            await qdrant_module.qdrant_service.upsert("medical_text", vector, payload)

        if neo4j_module.neo4j_client is not None:
            try:
                await neo4j_module.neo4j_client.upsert_document(
                    document_id=doc_id,
                    content=text,
                    source=source or "text_ingest",
                    entities=entities_found,
                )
            except Exception as exc:
                logger.warning("neo4j_upsert_skipped", doc_id=doc_id, error=str(exc))

        logger.info("text_ingested", doc_id=doc_id, chunks=len(chunks))
        return doc_id, entities_found

    async def ingest_image(
        self, image_bytes: bytes, metadata: dict[str, Any] | None = None
    ) -> tuple[str, str]:
        metadata = metadata or {}
        doc_id = str(uuid.uuid4())
        image_vector = self.image_embedder.embed_image(image_bytes)
        description = await self.image_embedder.generate_description(
            image_bytes, self.openai_client
        )

        payload = {
            "description": description,
            "doc_id": doc_id,
            "modality": "image",
            "metadata": metadata,
        }
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        await qdrant_module.qdrant_service.upsert("medical_images", image_vector, payload)

        text_vector = self.text_embedder.embed(description)
        text_payload = {
            "content": description,
            "doc_id": doc_id,
            "modality": "image_description",
            "metadata": metadata,
        }
        await qdrant_module.qdrant_service.upsert("medical_text", text_vector, text_payload)

        if neo4j_module.neo4j_client is not None:
            entities_found = self.entity_service.extract_entities(description)
            try:
                await neo4j_module.neo4j_client.upsert_document(
                    document_id=doc_id,
                    content=description,
                    source="image_description",
                    entities=entities_found,
                )
            except Exception as exc:
                logger.warning("neo4j_upsert_skipped", doc_id=doc_id, error=str(exc))

        logger.info("image_ingested", doc_id=doc_id)
        return doc_id, description

    async def ingest_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, str, float]:
        metadata = metadata or {}
        doc_id = str(uuid.uuid4())
        result = await self.audio_transcriber.transcribe(audio_bytes, filename)
        transcript = result["transcript"]

        vector = self.audio_transcriber.embed_transcript(transcript)
        payload = {
            "transcript": transcript,
            "duration": result["duration"],
            "language": result["language"],
            "doc_id": doc_id,
            "modality": "audio",
            "metadata": metadata,
        }
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        await qdrant_module.qdrant_service.upsert("medical_audio", vector, payload)
        await self.ingest_text(
            transcript, source="audio_transcript", metadata={"doc_id": doc_id, **metadata}
        )

        logger.info("audio_ingested", doc_id=doc_id, duration=result["duration"])
        return doc_id, transcript, float(result["duration"] or 0)

    async def ingest_lab_table(
        self,
        lab_values: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        metadata = metadata or {}
        doc_id = str(uuid.uuid4())
        vector, abnormal = self.table_embedder.embed_lab_values(lab_values)

        payload = {
            "lab_values": lab_values,
            "abnormal_values": abnormal,
            "doc_id": doc_id,
            "modality": "table",
            "metadata": metadata,
        }
        if qdrant_module.qdrant_service is None:
            raise RuntimeError("Qdrant service is not initialized.")
        await qdrant_module.qdrant_service.upsert("medical_tables", vector, payload)

        lab_text = "Lab values: " + ", ".join([f"{k}={v}" for k, v in lab_values.items()])
        await self.ingest_text(
            lab_text, source="lab_results", metadata={"doc_id": doc_id, **metadata}
        )

        logger.info("table_ingested", doc_id=doc_id, abnormal_count=len(abnormal))
        return doc_id, abnormal
