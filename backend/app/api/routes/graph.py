from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_graph_rag_service, get_neo4j_service, limiter
from app.core.graph_rag import GraphRAGService
from app.db.neo4j_client import Neo4jClient

router = APIRouter(tags=["graph"])


def _safe_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _safe_json_value(v) for k, v in value.items()}
    return str(value)


def _serialize_node(node: Any) -> dict[str, Any] | None:
    if node is None:
        return None
    try:
        props = dict(node)
    except Exception:
        props = {}

    node_id = str(props.get("id") or props.get("name") or "")
    if not node_id:
        fallback_id = getattr(node, "element_id", None) or getattr(node, "id", None)
        node_id = str(fallback_id) if fallback_id is not None else ""
    if not node_id:
        return None

    labels = []
    try:
        labels = list(getattr(node, "labels", []) or [])
    except Exception:
        labels = []

    return {
        "id": node_id,
        "label": str(props.get("name") or node_id),
        "type": str(labels[0]) if labels else "Unknown",
        "properties": {
            str(k): _safe_json_value(v)
            for k, v in props.items()
            if k not in {"id", "name"} and v is not None
        },
    }


def _serialize_rel(rel: Any) -> dict[str, Any] | None:
    if rel is None:
        return None

    try:
        rel_props = dict(rel)
    except Exception:
        rel_props = {}

    start_node = getattr(rel, "start_node", None)
    end_node = getattr(rel, "end_node", None)
    if (start_node is None or end_node is None) and hasattr(rel, "nodes"):
        try:
            nodes = list(rel.nodes)
            if len(nodes) == 2:
                start_node, end_node = nodes[0], nodes[1]
        except Exception:
            pass

    source = _serialize_node(start_node) if start_node is not None else None
    target = _serialize_node(end_node) if end_node is not None else None
    if not source or not target:
        return None

    rel_type = getattr(rel, "type", None)
    if not rel_type:
        rel_type = rel_props.get("type", "RELATED_TO")

    return {
        "source": source["id"],
        "target": target["id"],
        "relationship": str(rel_type),
        "weight": 1.0,
        "properties": {
            str(k): _safe_json_value(v) for k, v in rel_props.items() if v is not None
        },
    }


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
    neo4j: Neo4jClient = Depends(get_neo4j_service),
):
    _ = request
    safe_depth = max(1, min(depth, 3))
    cypher = f"""
    MATCH (start)
    WHERE (start:Drug OR start:Disease OR start:Symptom OR start:Gene OR start:LabTest)
      AND toLower(coalesce(start.name, '')) = toLower($entity)
    OPTIONAL MATCH path = (start)-[*1..{safe_depth}]-(connected)
    WHERE connected IS NULL
       OR connected:Drug
       OR connected:Disease
       OR connected:Symptom
       OR connected:Gene
       OR connected:LabTest
    WITH collect(DISTINCT start) + collect(DISTINCT connected) AS raw_nodes,
         collect(path) AS raw_paths
    WITH [n IN raw_nodes WHERE n IS NOT NULL] AS nodes,
         [p IN raw_paths WHERE p IS NOT NULL] AS paths
    WITH nodes, reduce(all_rels = [], p IN paths | all_rels + relationships(p)) AS rels
    UNWIND CASE WHEN rels = [] THEN [NULL] ELSE rels END AS rel
    WITH nodes, collect(
      CASE
        WHEN rel IS NULL THEN NULL
        ELSE {{
          source: coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))),
          target: coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))),
          relationship: type(rel),
          properties: properties(rel)
        }}
      END
    ) AS rel_rows
    RETURN nodes, [row IN rel_rows WHERE row IS NOT NULL] AS rel_rows
    LIMIT 1
    """

    try:
        rows = await neo4j.execute_query(cypher, {"entity": entity.strip()})
    except Exception:
        return {"nodes": [], "edges": []}

    if not rows:
        return {"nodes": [], "edges": []}

    row = rows[0]
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

    for node in row.get("nodes", []) or []:
        parsed = _serialize_node(node)
        if parsed:
            nodes_by_id[parsed["id"]] = parsed

    for rel_row in row.get("rel_rows", []) or []:
        if not isinstance(rel_row, dict):
            continue
        source = str(rel_row.get("source", "") or "")
        target = str(rel_row.get("target", "") or "")
        relationship = str(rel_row.get("relationship", "") or "")
        if not source or not target or not relationship:
            continue
        properties = rel_row.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        parsed = {
            "source": source,
            "target": target,
            "relationship": relationship,
            "weight": 1.0,
            "properties": {str(k): _safe_json_value(v) for k, v in properties.items()},
        }
        key = (parsed["source"], parsed["target"], parsed["relationship"])
        edges_by_key[key] = parsed

    return {"nodes": list(nodes_by_id.values()), "edges": list(edges_by_key.values())}


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
    query_fulltext = """
    CALL db.index.fulltext.queryNodes("drug_search", $q) 
    YIELD node, score
    RETURN node, score, labels(node)[0] as label
    LIMIT 5
    """
    query_name = """
    MATCH (n)
    WHERE (n:Drug OR n:Disease OR n:Symptom OR n:Gene OR n:LabTest)
    AND toLower(n.name) CONTAINS toLower($q)
    RETURN n as node, 0.5 as score, labels(n)[0] as label
    LIMIT 10
    """

    combined: list[dict] = []
    try:
        combined.extend(await neo4j.execute_query(query_fulltext, {"q": q}))
    except Exception:
        pass
    combined.extend(await neo4j.execute_query(query_name, {"q": q}))

    deduped: dict[str, dict] = {}
    for row in combined:
        node = row.get("node")
        if not node:
            continue
        node_props = dict(node)
        node_id = str(node_props.get("id", node_props.get("name", "")))
        if not node_id:
            continue
        score = float(row.get("score", 0))
        item = {
            "id": node_id,
            "label": str(node_props.get("name", node_id)),
            "type": row.get("label", "Unknown"),
            "properties": {k: v for k, v in node_props.items() if k not in ["id", "name"]},
            "_score": score,
        }
        existing = deduped.get(node_id)
        if existing is None or score > float(existing.get("_score", 0)):
            deduped[node_id] = item

    sorted_results = sorted(
        deduped.values(), key=lambda x: float(x.get("_score", 0)), reverse=True
    )[:10]
    final_results = [
        {
            "id": item["id"],
            "label": item["label"],
            "type": item["type"],
            "properties": item["properties"],
        }
        for item in sorted_results
    ]
    return {"results": final_results}
