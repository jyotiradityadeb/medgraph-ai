import json
from typing import Any

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.api.deps import get_neo4j_service, get_qdrant_service
from app.config import get_settings
from app.core.multimodal import MultiModalIngestPipeline
from app.db.neo4j_client import Neo4jClient
from app.db.qdrant_client import QdrantService
from app.models.schemas import IngestRequest, IngestResponse

router = APIRouter(tags=["ingest"])
settings = get_settings()


def get_pipeline() -> MultiModalIngestPipeline:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return MultiModalIngestPipeline(client)


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
async def ingest_text(
    request: Request,
    payload: dict[str, Any],
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
) -> IngestResponse:
    _ = request
    validated = IngestRequest.model_validate(payload)
    pipeline = get_pipeline()
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
async def ingest_image(
    request: Request,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file.")
    parsed_metadata = _parse_metadata(metadata)
    pipeline = get_pipeline()
    document_id, description = await pipeline.ingest_image(
        image_bytes=image_bytes, metadata=parsed_metadata
    )
    return {"document_id": document_id, "description": description, "success": True}


@router.post("/audio")
async def ingest_audio(
    request: Request,
    file: UploadFile = File(...),
    metadata: str | None = Form(default=None),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    parsed_metadata = _parse_metadata(metadata)
    pipeline = get_pipeline()
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
async def ingest_table(
    request: Request,
    payload: TableIngestRequest,
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    metadata = {
        "patient_id": payload.patient_id,
        "timestamp": payload.timestamp,
        **payload.metadata,
    }
    pipeline = get_pipeline()
    document_id, abnormal_values = await pipeline.ingest_lab_table(
        payload.lab_values, metadata=metadata
    )
    return {"document_id": document_id, "abnormal_values": abnormal_values, "success": True}


@router.post("/pdf")
async def ingest_pdf(
    request: Request,
    file: UploadFile = File(...),
    _qdrant: QdrantService = Depends(get_qdrant_service),
    _neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only application/pdf is supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF file.")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {exc}") from exc

    full_text = "\n".join([page.get_text() for page in doc])
    if not full_text or len(full_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    pipeline = get_pipeline()
    doc_id, _entities = await pipeline.ingest_text(
        full_text,
        source=file.filename or "uploaded.pdf",
        metadata={"source_type": "pdf", "pages": len(doc)},
    )

    return {
        "document_id": doc_id,
        "success": True,
        "pages": len(doc),
        "characters": len(full_text),
    }
