import json
from typing import Any

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.api.deps import get_neo4j_service, get_openai_client, get_qdrant_service, limiter
from app.core.multimodal import MultiModalIngestPipeline
from app.db.neo4j_client import Neo4jClient
from app.db.qdrant_client import QdrantService
from app.models.schemas import IngestRequest, IngestResponse

router = APIRouter(tags=["ingest"])

_MAX_FILE_BYTES = 50_000_000


def _parse_metadata(raw_metadata: str | None) -> dict[str, Any]:
    if not raw_metadata:
        return {}
    try:
        value = json.loads(raw_metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object.")
    return value


class TableIngestRequest(BaseModel):
    lab_values: dict[str, float]
    patient_id: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/text", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_text(
    request: Request,
    payload: dict[str, Any],
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
) -> IngestResponse:
    validated = IngestRequest.model_validate(payload)
    pipeline = MultiModalIngestPipeline(openai_client)
    doc_id, entities = await pipeline.ingest_text(
        validated.content, source=validated.source, metadata=validated.metadata
    )
    return IngestResponse(
        success=True,
        document_id=doc_id,
        message="Text content ingested successfully.",
        entities_found=entities,
    )


@router.post("/image")
@limiter.limit("10/minute")
async def ingest_image(
    request: Request,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file.")
    if len(image_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")
    parsed_metadata = _parse_metadata(metadata)
    pipeline = MultiModalIngestPipeline(openai_client)
    document_id, description = await pipeline.ingest_image(
        image_bytes=image_bytes, metadata=parsed_metadata
    )
    return {"document_id": document_id, "description": description, "success": True}


@router.post("/audio")
@limiter.limit("10/minute")
async def ingest_audio(
    request: Request,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(audio_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")
    parsed_metadata = _parse_metadata(metadata)
    pipeline = MultiModalIngestPipeline(openai_client)
    document_id, transcript, duration = await pipeline.ingest_audio(
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.mp3",
        metadata=parsed_metadata,
    )
    return {
        "document_id": document_id,
        "transcript": transcript,
        "duration": duration,
        "success": True,
    }


@router.post("/table")
@limiter.limit("10/minute")
async def ingest_table(
    request: Request,
    payload: TableIngestRequest,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    metadata = {
        "patient_id": payload.patient_id,
        "timestamp": payload.timestamp,
        **payload.metadata,
    }
    pipeline = MultiModalIngestPipeline(openai_client)
    document_id, abnormal_values = await pipeline.ingest_lab_table(
        payload.lab_values, metadata=metadata
    )
    return {"document_id": document_id, "abnormal_values": abnormal_values, "success": True}


@router.post("/pdf")
@limiter.limit("10/minute")
async def ingest_pdf(
    request: Request,
    file: UploadFile = File(...),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only application/pdf is supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF file.")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {exc}") from exc

    extracted_pages = [page.get_text() for page in doc]
    full_text = "\n".join(extracted_pages)
    clean_text = full_text.strip()
    if not clean_text or len(clean_text) < 50:
        clean_text = (
            f"PDF document uploaded: {file.filename or 'uploaded.pdf'}. "
            f"Pages: {len(doc)}. Text extraction was limited, but the document was ingested "
            "for demo retrieval indexing."
        )

    pipeline = MultiModalIngestPipeline(openai_client)
    doc_id, _entities = await pipeline.ingest_text(
        clean_text,
        source=file.filename or "uploaded.pdf",
        metadata={
            "source_type": "pdf",
            "pages": len(doc),
            "extraction_mode": "text" if len(full_text.strip()) >= 50 else "limited_fallback",
        },
    )

    return {
        "document_id": doc_id,
        "success": True,
        "pages": len(doc),
        "characters": len(clean_text),
    }
