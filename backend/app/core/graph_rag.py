from __future__ import annotations

import json
from typing import Any

import structlog

from app.models.schemas import GraphContext, GraphEdge, GraphNode, Source

logger = structlog.get_logger()


class GraphRAGService:
    def __init__(self, openai_client, neo4j_client):
        self.openai = openai_client
        self.neo4j = neo4j_client

    async def extract_entities(self, query: str) -> dict[str, list[str]]:
        """Use GPT-4o to extract medical entities from query."""
        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": 'Extract medical entities. Return JSON only: {"drugs": [], "diseases": [], "symptoms": [], "genes": [], "lab_tests": []}',
                },
                {"role": "user", "content": query},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        fallback = {"drugs": [], "diseases": [], "symptoms": [], "genes": [], "lab_tests": []}
        for key in fallback:
            value = parsed.get(key, [])
            fallback[key] = [str(v) for v in value] if isinstance(value, list) else []
        return fallback

    async def traverse_graph(self, entities: dict[str, list[str]], depth: int = 2) -> GraphContext:
        all_names = []
        for entity_list in entities.values():
            all_names.extend([str(e).lower() for e in entity_list])

        if not all_names:
            return GraphContext(nodes=[], edges=[], traversal_depth=0, entities_found=[])

        safe_depth = max(1, min(depth, 3))
        cypher = f"""
        MATCH (start)
        WHERE (start:Drug OR start:Disease OR start:Symptom OR start:Gene OR start:LabTest)
        AND toLower(start.name) IN $names
        WITH start
        MATCH path = (start)-[r*1..{safe_depth}]-(connected)
        WHERE connected:Drug OR connected:Disease OR connected:Symptom OR connected:Gene OR connected:LabTest
        WITH start, relationships(path) AS rels, nodes(path) AS path_nodes
        UNWIND path_nodes AS n
        WITH COLLECT(DISTINCT n) AS all_nodes, COLLECT(DISTINCT rels) AS all_rels
        RETURN all_nodes, all_rels
        LIMIT 1
        """

        try:
            results = await self.neo4j.execute_query(cypher, {"names": all_names})
        except Exception as exc:
            logger.warning("graph_traversal_primary_failed", error=str(exc))
            simpler_cypher = """
            MATCH (start)-[r]-(connected)
            WHERE toLower(start.name) IN $names
            AND (connected:Drug OR connected:Disease OR connected:Symptom OR connected:Gene OR connected:LabTest)
            RETURN start, r, connected
            LIMIT 80
            """
            results = await self.neo4j.execute_query(simpler_cypher, {"names": all_names})

        nodes_map: dict[str, GraphNode] = {}
        edges_map: dict[tuple[str, str, str], GraphEdge] = {}

        def parse_node(node: Any) -> GraphNode | None:
            if not node:
                return None
            props = dict(node)
            node_id = str(props.get("id", props.get("name", "")))
            if not node_id:
                return None
            labels = list(node.labels) if hasattr(node, "labels") else ["Unknown"]
            return GraphNode(
                id=node_id,
                label=str(props.get("name", node_id)),
                type=labels[0] if labels else "Unknown",
                properties={
                    k: str(v) for k, v in props.items() if k not in ["id", "name"] and v is not None
                },
            )

        def upsert_edge(rel: Any):
            if not rel:
                return
            rel_props = dict(rel)
            s_node = rel.start_node
            t_node = rel.end_node
            source_id = str(dict(s_node).get("id", dict(s_node).get("name", "")))
            target_id = str(dict(t_node).get("id", dict(t_node).get("name", "")))
            rel_type = rel.type if hasattr(rel, "type") else str(type(rel).__name__)
            key = (source_id, target_id, rel_type)
            edges_map[key] = GraphEdge(
                source=source_id,
                target=target_id,
                relationship=rel_type,
                weight=1.0,
                properties={k: str(v) for k, v in rel_props.items() if v is not None},
            )

        for record in results:
            if "all_nodes" in record:
                for node in record.get("all_nodes", []) or []:
                    parsed = parse_node(node)
                    if parsed:
                        nodes_map[parsed.id] = parsed
            if "all_rels" in record:
                rel_lists = record.get("all_rels", []) or []
                for rel_list in rel_lists:
                    if isinstance(rel_list, list):
                        for rel in rel_list:
                            upsert_edge(rel)

            for key in ["start", "connected"]:
                if key in record and record[key]:
                    parsed = parse_node(record[key])
                    if parsed:
                        nodes_map[parsed.id] = parsed
            if "r" in record and record["r"]:
                upsert_edge(record["r"])

        entities_found = [n.label for n in nodes_map.values() if n.label.lower() in all_names]

        return GraphContext(
            nodes=list(nodes_map.values())[:50],
            edges=list(edges_map.values())[:100],
            traversal_depth=safe_depth,
            entities_found=entities_found,
        )

    def build_context_string(self, sources: list[Source], graph_context: GraphContext) -> str:
        parts = ["=== RETRIEVED CLINICAL DOCUMENTS ==="]
        for i, source in enumerate(sources[:6]):
            modality_label = source.modality.upper()
            parts.append(
                f"[{i + 1}] ({modality_label}, relevance: {source.score:.2f})\n{source.content[:400]}"
            )

        if graph_context.nodes:
            parts.append("\n=== MEDICAL KNOWLEDGE GRAPH CONTEXT ===")
            parts.append(f"Entities found: {', '.join(set(graph_context.entities_found))}")
            parts.append(
                f"Graph traversal: {len(graph_context.nodes)} nodes, {len(graph_context.edges)} relationships\n"
            )

            for edge in graph_context.edges[:30]:
                props_str = ""
                if edge.properties:
                    important_props = {
                        k: v
                        for k, v in edge.properties.items()
                        if k
                        in [
                            "severity",
                            "efficacy_score",
                            "evidence_level",
                            "frequency",
                            "mechanism",
                        ]
                    }
                    if important_props:
                        props_str = (
                            " (" + ", ".join(f"{k}: {v}" for k, v in important_props.items()) + ")"
                        )
                parts.append(f"  {edge.source} --[{edge.relationship}]--> {edge.target}{props_str}")

        return "\n".join(parts)
