from __future__ import annotations

from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase

logger = structlog.get_logger()


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def verify_connectivity(self) -> bool:
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error("neo4j_connection_failed", error=str(e))
            return False

    async def create_schema(self):
        """Create all constraints and indexes."""
        constraints = [
            "CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (d:Drug) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE",
            "CREATE CONSTRAINT protein_id IF NOT EXISTS FOR (p:Protein) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT labtest_id IF NOT EXISTS FOR (l:LabTest) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT treatment_id IF NOT EXISTS FOR (t:Treatment) REQUIRE t.id IS UNIQUE",
            "CREATE FULLTEXT INDEX drug_search IF NOT EXISTS FOR (d:Drug) ON EACH [d.name, d.generic_name, d.description]",
            "CREATE FULLTEXT INDEX disease_search IF NOT EXISTS FOR (d:Disease) ON EACH [d.name, d.description, d.icd10_code]",
            "CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)",
            "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
            "CREATE INDEX symptom_name IF NOT EXISTS FOR (s:Symptom) ON (s.name)",
        ]
        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    logger.warning(
                        "constraint_already_exists", constraint=constraint[:50], error=str(e)
                    )
        logger.info("neo4j_schema_created")

    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        payload = params or {}
        async with self.driver.session() as session:
            result = await session.run(query, payload)
            return [record.data() async for record in result]

    async def execute_write(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        payload = params or {}

        async def _work(tx):
            result = await tx.run(query, payload)
            return [record.data() async for record in result]

        async with self.driver.session() as session:
            return await session.execute_write(_work)

    async def upsert_document(
        self, document_id: str, content: str, source: str, entities: list[str]
    ) -> None:
        await self.execute_write(
            """
            MERGE (d:Document {id: $document_id})
            SET d.content = $content, d.source = $source, d.updated_at = datetime()
            """,
            {"document_id": document_id, "content": content, "source": source},
        )
        for entity in entities:
            await self.execute_write(
                """
                MERGE (e:Entity {name: $entity})
                ON CREATE SET e.created_at = datetime()
                MERGE (d:Document {id: $document_id})
                MERGE (d)-[:MENTIONS]->(e)
                """,
                {"entity": entity, "document_id": document_id},
            )

    async def link_document_to_graph_nodes(
        self, document_id: str, entity_names: list[str]
    ) -> None:
        """Create (Document)-[:MENTIONS]->(typed_node) edges for matched graph entities."""
        if not entity_names:
            return
        for name in entity_names:
            try:
                await self.execute_write(
                    """
                    MATCH (node)
                    WHERE (node:Drug OR node:Disease OR node:Symptom OR node:Gene
                           OR node:LabTest OR node:Treatment OR node:Protein)
                      AND toLower(coalesce(node.name, '')) = toLower($name)
                    WITH node LIMIT 1
                    MATCH (doc:Document {id: $doc_id})
                    MERGE (doc)-[r:MENTIONS]->(node)
                    SET r.source_doc = $doc_id
                    """,
                    {"name": name, "doc_id": document_id},
                )
            except Exception as exc:
                logger.warning(
                    "link_document_to_graph_nodes.failed",
                    name=name,
                    doc_id=document_id,
                    error=str(exc),
                )

    async def get_basic_stats(self) -> dict[str, int]:
        nodes = await self.execute_query("MATCH (n) RETURN count(n) AS c")
        rels = await self.execute_query("MATCH ()-[r]->() RETURN count(r) AS c")
        return {
            "nodes": int(nodes[0]["c"]) if nodes else 0,
            "relationships": int(rels[0]["c"]) if rels else 0,
        }

    async def close(self):
        await self.driver.close()


neo4j_client: Neo4jClient | None = None


async def get_neo4j() -> Neo4jClient:
    return neo4j_client
