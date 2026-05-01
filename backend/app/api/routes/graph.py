from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_graph_rag_service, get_neo4j_service, limiter
from app.core.graph_rag import GraphRAGService
from app.db.neo4j_client import Neo4jClient

router = APIRouter(tags=["graph"])


@router.get("/context")
@limiter.limit("60/minute")
async def graph_context(
    request: Request,
    entities: str = Query(default="", description="Comma-separated entity names"),
    depth: int = Query(default=2, ge=1, le=3),
    graph_rag: GraphRAGService = Depends(get_graph_rag_service),
):
    _ = request
    names = [item.strip() for item in entities.split(",") if item.strip()]
    grouped = {
        "drugs": names,
        "diseases": names,
        "symptoms": names,
        "genes": names,
        "lab_tests": names,
    }
    context = await graph_rag.traverse_graph(grouped, depth=depth)
    return context.model_dump()


@router.get("/explore")
@limiter.limit("60/minute")
async def explore_graph(
    request: Request,
    entity: str = Query(..., min_length=1),
    depth: int = Query(default=2, ge=1, le=3),
    graph_rag: GraphRAGService = Depends(get_graph_rag_service),
):
    _ = request
    entities = {
        "drugs": [entity],
        "diseases": [entity],
        "symptoms": [entity],
        "genes": [entity],
        "lab_tests": [entity],
    }
    context = await graph_rag.traverse_graph(entities=entities, depth=depth)
    return {
        "nodes": [node.model_dump() for node in context.nodes],
        "edges": [edge.model_dump() for edge in context.edges],
        "center_entity": entity,
        "stats": {"node_count": len(context.nodes), "edge_count": len(context.edges)},
    }


@router.get("/stats")
@limiter.limit("60/minute")
async def graph_stats(request: Request, neo4j: Neo4jClient = Depends(get_neo4j_service)):
    _ = request
    label_rows = await neo4j.execute_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
    )
    rel_rows = await neo4j.execute_query(
        "MATCH ()-[r]->() RETURN type(r) AS relationship_type, count(r) AS count ORDER BY count DESC"
    )
    return {"node_counts_by_label": label_rows, "relationship_counts_by_type": rel_rows}


@router.get("/search")
@limiter.limit("60/minute")
async def graph_search(
    request: Request,
    q: str = Query(..., min_length=1),
    neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    rows = await neo4j.execute_query(
        """
        CALL db.index.fulltext.queryNodes("drug_search", $q) YIELD node, score
        RETURN node.id AS id, node.name AS name, labels(node)[0] AS label, score
        ORDER BY score DESC
        LIMIT 10
        """,
        {"q": q},
    )
    return {"query": q, "results": rows}
