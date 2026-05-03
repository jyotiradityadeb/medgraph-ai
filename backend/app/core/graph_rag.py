from __future__ import annotations

import json
import re
from typing import Any

import structlog
from openai import APIError, APITimeoutError, AuthenticationError, RateLimitError

from app.models.schemas import GraphContext, GraphEdge, GraphNode, Source

logger = structlog.get_logger()


class GraphRAGService:
    RULE_BASED_ALIASES: dict[str, tuple[str, str]] = {
        "warfarin": ("drugs", "Warfarin"),
        "aspirin": ("drugs", "Aspirin"),
        "metformin": ("drugs", "Metformin"),
        "furosemide": ("drugs", "Furosemide"),
        "lisinopril": ("drugs", "Lisinopril"),
        "ckd": ("diseases", "Chronic Kidney Disease"),
        "chronic kidney disease": ("diseases", "Chronic Kidney Disease"),
        "t2dm": ("diseases", "Type 2 Diabetes Mellitus"),
        "diabetes": ("diseases", "Type 2 Diabetes Mellitus"),
        "hba1c": ("lab_tests", "HbA1c"),
        "bnp": ("lab_tests", "BNP"),
        "egfr": ("lab_tests", "eGFR"),
        "inr": ("lab_tests", "INR"),
        "cyp2c9": ("genes", "CYP2C9"),
        "vkorc1": ("genes", "VKORC1"),
        "dyspnea": ("symptoms", "Dyspnea"),
        "orthopnea": ("symptoms", "Orthopnea"),
        "edema": ("symptoms", "Peripheral edema"),
        "hypokalemia": ("symptoms", "Hypokalemia"),
    }

    def __init__(self, openai_client, neo4j_client):
        self.openai = openai_client
        self.neo4j = neo4j_client

    def extract_entities_rule_based(self, query: str) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {
            "drugs": [],
            "diseases": [],
            "symptoms": [],
            "genes": [],
            "lab_tests": [],
        }
        text = query.lower()

        for alias, (bucket, canonical) in self.RULE_BASED_ALIASES.items():
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, text):
                if canonical not in found[bucket]:
                    found[bucket].append(canonical)
        return found

    def merge_entities(
        self, primary: dict[str, list[str]] | None, secondary: dict[str, list[str]] | None
    ) -> dict[str, list[str]]:
        merged: dict[str, list[str]] = {
            "drugs": [],
            "diseases": [],
            "symptoms": [],
            "genes": [],
            "lab_tests": [],
        }
        for source in [primary or {}, secondary or {}]:
            for key in merged:
                values = source.get(key, [])
                if not isinstance(values, list):
                    continue
                for value in values:
                    item = str(value).strip()
                    if item and item not in merged[key]:
                        merged[key].append(item)
        return merged

    async def extract_entities(self, query: str) -> dict[str, list[str]]:
        """Extract entities with rule-based aliases, then enrich with GPT when available."""
        fallback = self.extract_entities_rule_based(query)
        try:
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
            llm_entities = {k: parsed.get(k, []) for k in fallback}
            fallback = self.merge_entities(fallback, llm_entities)
        except (AuthenticationError, APIError, RateLimitError, APITimeoutError, TimeoutError) as exc:
            logger.warning("entity_extraction_openai_fallback", error=str(exc))
        except Exception as exc:
            logger.warning("entity_extraction_failed", error=str(exc))
        return fallback

    async def traverse_graph(self, entities: dict[str, list[str]], depth: int = 2) -> GraphContext:
        all_names: list[str] = []
        for entity_list in entities.values():
            all_names.extend([str(e).strip() for e in entity_list if str(e).strip()])

        deduped_names: list[str] = []
        seen: set[str] = set()
        for name in all_names:
            lowered = name.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped_names.append(name)

        if not deduped_names:
            return GraphContext(nodes=[], edges=[], traversal_depth=0, entities_found=[])

        safe_depth = max(1, min(depth, 3))
        cypher = """
        MATCH (start)
        WHERE (start:Drug OR start:Disease OR start:Symptom OR start:Gene OR start:LabTest)
          AND toLower(coalesce(start.name, "")) = toLower($name)
        OPTIONAL MATCH path = (start)-[*1..DEPTH]-(connected)
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
            ELSE {
              source_id: coalesce(startNode(rel).id, startNode(rel).name, elementId(startNode(rel))),
              target_id: coalesce(endNode(rel).id, endNode(rel).name, elementId(endNode(rel))),
              relationship: type(rel),
              properties: properties(rel)
            }
          END
        ) AS rel_rows
        RETURN nodes, [row IN rel_rows WHERE row IS NOT NULL] AS rel_rows
        LIMIT 1
        """
        cypher = cypher.replace("DEPTH", str(safe_depth))

        nodes_map: dict[str, GraphNode] = {}
        edges_map: dict[tuple[str, str, str], GraphEdge] = {}

        def parse_node(node: Any) -> GraphNode | None:
            if not node:
                return None
            try:
                props = dict(node)
            except Exception:
                props = {}
            node_id = str(props.get("id", props.get("name", "")) or "")
            if not node_id:
                fallback_id = getattr(node, "element_id", None) or getattr(node, "id", None)
                if fallback_id is not None:
                    node_id = str(fallback_id)
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

        def upsert_edge(edge_row: Any):
            if not edge_row:
                return
            if not isinstance(edge_row, dict):
                return
            source_id = str(edge_row.get("source_id", "") or "")
            target_id = str(edge_row.get("target_id", "") or "")
            rel_type = str(edge_row.get("relationship", "") or "")
            if not source_id or not target_id or not rel_type:
                return
            raw_props = edge_row.get("properties", {})
            rel_props = raw_props if isinstance(raw_props, dict) else {}
            key = (source_id, target_id, rel_type)
            edges_map[key] = GraphEdge(
                source=source_id,
                target=target_id,
                relationship=rel_type,
                weight=1.0,
                properties={k: str(v) for k, v in rel_props.items() if v is not None},
            )

        for entity_name in deduped_names:
            try:
                results = await self.neo4j.execute_query(cypher, {"name": entity_name})
            except Exception as exc:
                logger.warning("graph_traversal_primary_failed", entity=entity_name, error=str(exc))
                continue

            for record in results:
                for node in record.get("nodes", []) or []:
                    parsed = parse_node(node)
                    if parsed:
                        nodes_map[parsed.id] = parsed

                for rel_row in record.get("rel_rows", []) or []:
                    upsert_edge(rel_row)

        lowered_names = {name.lower() for name in deduped_names}
        entities_found = [n.label for n in nodes_map.values() if n.label.lower() in lowered_names]

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
