from __future__ import annotations

import json
import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.api.deps import get_neo4j_service, get_openai_client, get_qdrant_service, limiter
from app.core.cache import query_cache
from app.core.graph_rag import GraphRAGService
from app.core.llm import LLMSynthesizer
from app.core.query_processor import QueryProcessor
from app.core.retrieval import MultiModalRetriever
from app.db.neo4j_client import Neo4jClient
from app.db.qdrant_client import QdrantService
from app.models.schemas import GraphContext, QueryRequest, Source
from app.utils.metrics import metrics

router = APIRouter(tags=["query"])
logger = structlog.get_logger()

query_history: list[dict[str, Any]] = []


@router.post("/query")
@router.post("")
@limiter.limit("60/minute")
async def query(
    request: Request,
    payload: QueryRequest,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_service),
    _qdrant: QdrantService = Depends(get_qdrant_service),
):
    async def event_stream():
        start = time.time()
        processor = QueryProcessor(openai_client)
        retriever = MultiModalRetriever()
        graph_service = GraphRAGService(openai_client, neo4j_client)
        synthesizer = LLMSynthesizer(openai_client)

        expanded_query = processor.expand_abbreviations(payload.query)
        full_answer = ""

        try:
            cache_entry = query_cache.get(expanded_query, payload.modalities, payload.top_k)
            if cache_entry:
                intent_result = cache_entry.get("intent_result", {"intent": "general"})
                sources = [Source.model_validate(item) for item in cache_entry.get("sources", [])]
                graph_context = GraphContext.model_validate(
                    cache_entry.get(
                        "graph_context",
                        {"nodes": [], "edges": [], "traversal_depth": 0, "entities_found": []},
                    )
                )
                failed_modalities = list(cache_entry.get("failed_modalities", []))
                graph_unavailable = bool(cache_entry.get("graph_unavailable", False))
            else:
                intent_result = await processor.classify_intent(expanded_query)
                entities = intent_result.get(
                    "extracted_entities",
                    {"drugs": [], "diseases": [], "symptoms": [], "genes": [], "lab_tests": []},
                )

                sources, failed_modalities = await retriever.retrieve_all_with_diagnostics(
                    expanded_query,
                    payload.modalities,
                    payload.top_k,
                )
                for modality in failed_modalities:
                    metrics.record_error(f"retrieval_{modality}")

                graph_unavailable = False
                if payload.use_graph:
                    try:
                        graph_context = await graph_service.traverse_graph(
                            entities, payload.graph_depth
                        )
                    except Exception as exc:
                        logger.warning("graph_traversal_degraded", error=str(exc))
                        metrics.record_error("graph_error")
                        graph_context = GraphContext(
                            nodes=[], edges=[], traversal_depth=0, entities_found=[]
                        )
                        graph_unavailable = True
                else:
                    graph_context = GraphContext(
                        nodes=[], edges=[], traversal_depth=0, entities_found=[]
                    )

                query_cache.set(
                    expanded_query,
                    payload.modalities,
                    payload.top_k,
                    {
                        "intent_result": intent_result,
                        "sources": [item.model_dump() for item in sources],
                        "graph_context": graph_context.model_dump(),
                        "failed_modalities": failed_modalities,
                        "graph_unavailable": graph_unavailable,
                    },
                )

            modalities_used = sorted({s.modality for s in sources})
            confidence = min(0.95, len(sources) * 0.1 + len(graph_context.nodes) * 0.02)

            metadata = {
                "type": "metadata",
                "intent": intent_result.get("intent", "general"),
                "confidence": round(confidence, 2),
                "modalities_used": modalities_used,
                "graph_nodes_count": len(graph_context.nodes),
                "graph_edges_count": len(graph_context.edges),
                "sources_count": len(sources),
                "entities_found": graph_context.entities_found,
                "graph_unavailable": graph_unavailable,
                "failed_modalities": failed_modalities,
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            context = graph_service.build_context_string(sources, graph_context)

            try:
                stream = await synthesizer.generate_streaming(
                    expanded_query, context, payload.model
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_answer += content
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
            except Exception as exc:
                logger.warning("llm_stream_degraded", error=str(exc))
                metrics.record_error("llm_stream_error")
                yield f"data: {json.dumps({'type': 'error', 'message': f'LLM streaming interrupted: {exc}'})}\n\n"

            processing_time = round(time.time() - start, 2)
            metrics.record_query(processing_time * 1000, modalities_used, len(graph_context.nodes))
            done_event = {
                "type": "done",
                "processing_time": processing_time,
                "sources": [s.model_dump() for s in sources],
                "graph_context": graph_context.model_dump(),
            }
            yield f"data: {json.dumps(done_event)}\n\n"

            query_history.append(
                {
                    "query": payload.query,
                    "intent": intent_result.get("intent"),
                    "processing_time": processing_time,
                    "sources_count": len(sources),
                    "graph_nodes": len(graph_context.nodes),
                    "timestamp": time.time(),
                    "answer_preview": full_answer[:250],
                }
            )
            if len(query_history) > 50:
                query_history.pop(0)
        except Exception as exc:
            logger.error("query_failed", error=str(exc))
            metrics.record_error("query_error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/query/history")
@router.get("/history")
@limiter.limit("60/minute")
async def get_history(request: Request):
    _ = request
    return {"history": list(reversed(query_history[-20:]))}
