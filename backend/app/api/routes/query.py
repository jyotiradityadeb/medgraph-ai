import json
import time
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import APIError, APITimeoutError, AsyncOpenAI, AuthenticationError, RateLimitError

from app.api.deps import get_neo4j_service, get_openai_client, get_qdrant_service
from app.config import get_settings
from app.core.cache import query_cache
from app.core.graph_rag import GraphRAGService
from app.core.llm import LLMSynthesizer, _check_answer_grounding
from app.core.query_processor import QueryProcessor
from app.core.retrieval import MultiModalRetriever
from app.db.neo4j_client import Neo4jClient
from app.db.qdrant_client import QdrantService
from app.models.schemas import GraphContext, QueryRequest, Source
from app.utils.audit_log import audit_log
from app.utils.metrics import metrics

router = APIRouter(tags=["query"])
logger = structlog.get_logger()

_HISTORY_KEY = "query_history"
_HISTORY_MAX = 500


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)


@router.post("/query")
@router.post("")
async def query(
    request: Request,
    payload: dict[str, Any],
    openai_client: AsyncOpenAI = Depends(get_openai_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_service),
    _qdrant: QdrantService = Depends(get_qdrant_service),
):
    query_request = QueryRequest.model_validate(payload)
    if not query_request.query.strip():
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': 'Query cannot be empty.'})}\n\n"]),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            status_code=400,
        )

    async def event_stream():
        start = time.time()
        processor = QueryProcessor(openai_client)
        retriever = MultiModalRetriever()
        graph_service = GraphRAGService(openai_client, neo4j_client)
        synthesizer = LLMSynthesizer(openai_client)

        expanded_query = processor.expand_abbreviations(query_request.query)
        full_answer = ""

        try:
            cache_entry = await query_cache.get(
                expanded_query, query_request.modalities, query_request.top_k
            )
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
                try:
                    intent_result = await processor.classify_intent(expanded_query)
                except (
                    AuthenticationError,
                    APIError,
                    RateLimitError,
                    APITimeoutError,
                    TimeoutError,
                ) as exc:
                    logger.warning("intent_classification_openai_fallback", error=str(exc))
                    intent_result = {
                        "intent": "general",
                        "relevant_modalities": query_request.modalities,
                        "extracted_entities": {
                            "drugs": [],
                            "diseases": [],
                            "symptoms": [],
                            "genes": [],
                            "lab_tests": [],
                        },
                        "complexity": "simple",
                        "requires_graph": query_request.use_graph,
                    }
                except Exception as exc:
                    logger.warning("intent_classification_fallback", error=str(exc))
                    intent_result = {
                        "intent": "general",
                        "relevant_modalities": query_request.modalities,
                        "extracted_entities": {
                            "drugs": [],
                            "diseases": [],
                            "symptoms": [],
                            "genes": [],
                            "lab_tests": [],
                        },
                        "complexity": "simple",
                        "requires_graph": query_request.use_graph,
                    }
                intent_entities = intent_result.get(
                    "extracted_entities",
                    {"drugs": [], "diseases": [], "symptoms": [], "genes": [], "lab_tests": []},
                )
                rule_entities = graph_service.extract_entities_rule_based(expanded_query)
                entities = graph_service.merge_entities(intent_entities, rule_entities)
                intent_result["extracted_entities"] = entities

                try:
                    sources, failed_modalities = await retriever.retrieve_all_with_diagnostics(
                        expanded_query,
                        query_request.modalities,
                        query_request.top_k,
                    )
                except Exception as exc:
                    logger.error("retrieval_failed", error=str(exc))
                    await metrics.record_error("retrieval_error")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Retrieval service unavailable.'})}\n\n"
                    return
                for modality in failed_modalities:
                    await metrics.record_error(f"retrieval_{modality}")

                graph_unavailable = False
                if query_request.use_graph:
                    try:
                        graph_context = await graph_service.traverse_graph(
                            entities, query_request.graph_depth
                        )
                    except Exception as exc:
                        logger.warning("graph_traversal_degraded", error=str(exc))
                        await metrics.record_error("graph_error")
                        graph_context = GraphContext(
                            nodes=[], edges=[], traversal_depth=0, entities_found=[]
                        )
                        graph_unavailable = True
                else:
                    graph_context = GraphContext(
                        nodes=[], edges=[], traversal_depth=0, entities_found=[]
                    )

                await query_cache.set(
                    expanded_query,
                    query_request.modalities,
                    query_request.top_k,
                    {
                        "intent_result": intent_result,
                        "sources": [item.model_dump() for item in sources],
                        "graph_context": graph_context.model_dump(),
                        "failed_modalities": failed_modalities,
                        "graph_unavailable": graph_unavailable,
                    },
                )

            modalities_used = sorted({s.modality for s in sources})

            if sources:
                avg_score = sum(s.score for s in sources) / len(sources)
                graph_boost = min(0.15, len(graph_context.nodes) * 0.005)
                confidence = round(min(0.95, avg_score + graph_boost), 2)
            else:
                confidence = 0.0

            context = graph_service.build_context_string(sources, graph_context)
            stream_result = await synthesizer.generate_streaming(
                expanded_query,
                context,
                query_request.model,
                retrieved_chunks=sources,
                graph_context=graph_context.model_dump(),
            )
            mode = stream_result.get("mode", "live")
            reason = stream_result.get("reason", "")
            llm_status = stream_result.get("llm_status", "ok")
            stream = stream_result["stream"]

            metadata = {
                "type": "metadata",
                "intent": intent_result.get("intent", "general"),
                "confidence": confidence,
                "modalities_used": modalities_used,
                "graph_nodes_count": len(graph_context.nodes),
                "graph_edges_count": len(graph_context.edges),
                "sources_count": len(sources),
                "entities_found": graph_context.entities_found,
                "graph_unavailable": graph_unavailable,
                "failed_modalities": failed_modalities,
                "mode": mode,
                "reason": reason,
                "llm_status": llm_status,
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            stream_had_content = False
            try:
                async for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_answer += content
                        stream_had_content = True
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
            except Exception as exc:
                logger.warning("llm_stream_degraded", error=str(exc))
                await metrics.record_error("llm_stream_error")
                fallback_payload = synthesizer.build_fallback_payload(
                    expanded_query,
                    context,
                    retrieved_chunks=sources,
                    graph_context=graph_context.model_dump(),
                )
                llm_status = "fallback"
                yield f"data: {json.dumps({'type': 'metadata', 'mode': fallback_payload['mode'], 'reason': fallback_payload['reason'], 'intent': intent_result.get('intent', 'general'), 'confidence': confidence, 'modalities_used': modalities_used, 'graph_nodes_count': len(graph_context.nodes), 'graph_edges_count': len(graph_context.edges), 'sources_count': len(sources), 'entities_found': graph_context.entities_found, 'graph_unavailable': graph_unavailable, 'failed_modalities': failed_modalities, 'llm_status': llm_status})}\n\n"
                full_answer = ""
                for line in fallback_payload["answer"].splitlines():
                    content = f"{line}\n"
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
                stream_had_content = True

            if not stream_had_content or not full_answer.strip():
                logger.warning("llm_stream_empty_fallback")
                fallback_payload = synthesizer.build_fallback_payload(
                    expanded_query,
                    context,
                    retrieved_chunks=sources,
                    graph_context=graph_context.model_dump(),
                )
                llm_status = "fallback"
                yield f"data: {json.dumps({'type': 'metadata', 'mode': fallback_payload['mode'], 'reason': fallback_payload['reason'], 'intent': intent_result.get('intent', 'general'), 'confidence': confidence, 'modalities_used': modalities_used, 'graph_nodes_count': len(graph_context.nodes), 'graph_edges_count': len(graph_context.edges), 'sources_count': len(sources), 'entities_found': graph_context.entities_found, 'graph_unavailable': graph_unavailable, 'failed_modalities': failed_modalities, 'llm_status': llm_status})}\n\n"
                full_answer = ""
                for line in fallback_payload["answer"].splitlines():
                    content = f"{line}\n"
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"

            processing_time = round(time.time() - start, 2)
            await metrics.record_query(
                processing_time * 1000, modalities_used, len(graph_context.nodes)
            )

            grounding_check, cited_sources = _check_answer_grounding(
                full_answer, sources, graph_context.model_dump()
            )

            done_event = {
                "type": "done",
                "processing_time": processing_time,
                "llm_status": llm_status,
                "grounding_check": grounding_check,
                "cited_sources": cited_sources,
                "sources": [s.model_dump() for s in sources],
                "graph_context": {
                    **graph_context.model_dump(),
                    "relationships": [
                        {
                            "source": edge.source,
                            "target": edge.target,
                            "relationship": edge.relationship,
                        }
                        for edge in graph_context.edges
                    ],
                },
            }
            yield f"data: {json.dumps(done_event)}\n\n"

            audit_log.log_query(
                query=expanded_query,
                intent=intent_result.get("intent", "general"),
                sources_count=len(sources),
                graph_nodes_count=len(graph_context.nodes),
                llm_status=llm_status,
                processing_time_ms=processing_time * 1000,
                extra={"grounding_check": grounding_check},
            )

            history_entry = json.dumps(
                {
                    "query": query_request.query,
                    "intent": intent_result.get("intent"),
                    "processing_time": processing_time,
                    "sources_count": len(sources),
                    "graph_nodes": len(graph_context.nodes),
                    "timestamp": time.time(),
                    "answer_preview": full_answer[:250],
                }
            )
            try:
                r = _get_redis()
                await r.lpush(_HISTORY_KEY, history_entry)
                await r.ltrim(_HISTORY_KEY, 0, _HISTORY_MAX - 1)
                await r.aclose()
            except Exception as exc:
                logger.warning("query_history.redis.failed", error=str(exc))

        except Exception as exc:
            logger.error("query_failed", error=str(exc))
            await metrics.record_error("query_error")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Query failed due to retrieval/backend issue.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/query/history")
@router.get("/history")
async def get_history(request: Request):
    _ = request
    try:
        r = _get_redis()
        raw = await r.lrange(_HISTORY_KEY, 0, 19)
        await r.aclose()
        return {"history": [json.loads(item) for item in raw]}
    except Exception as exc:
        logger.warning("query_history.get.failed", error=str(exc))
        return {"history": []}
