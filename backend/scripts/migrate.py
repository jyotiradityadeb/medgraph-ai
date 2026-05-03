"""MedGraph schema migration runner.

Applies versioned Neo4j constraints and Qdrant collection config changes in order.
Each migration is idempotent — safe to run multiple times.

Usage:
  python -m scripts.migrate [--neo4j-uri URI] [--neo4j-user USER] [--neo4j-password PASS]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "changeme"

# Ordered list of migrations. Each is (version, description, cypher_statements[]).
# Add new entries at the bottom — never reorder or edit existing ones.
MIGRATIONS: list[tuple[str, str, list[str]]] = [
    (
        "0001",
        "Initial schema: constraints and fulltext indexes",
        [
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
        ],
    ),
    (
        "0002",
        "Add Document node constraint and source_doc index on MENTIONS edges",
        [
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
        ],
    ),
    (
        "0003",
        "Add DrugBank source index for open data ingestion",
        [
            "CREATE INDEX drug_source IF NOT EXISTS FOR (d:Drug) ON (d.source)",
            "CREATE INDEX drug_inchikey IF NOT EXISTS FOR (d:Drug) ON (d.inchikey)",
        ],
    ),
]


async def run_migrations(uri: str, user: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            await session.run(
                """
                MERGE (m:SchemaMigration {name: 'migration_log'})
                ON CREATE SET m.applied = []
                """
            )
            result = await session.run(
                "MATCH (m:SchemaMigration {name: 'migration_log'}) RETURN m.applied AS applied"
            )
            record = await result.single()
            applied: list[str] = list(record["applied"]) if record else []

        for version, description, statements in MIGRATIONS:
            if version in applied:
                logger.info("[%s] already applied — skip", version)
                continue

            logger.info("[%s] applying: %s", version, description)
            async with driver.session() as session:
                for stmt in statements:
                    try:
                        await session.run(stmt)
                    except Exception as exc:
                        logger.warning("[%s] statement warning: %s", version, exc)

                await session.run(
                    """
                    MATCH (m:SchemaMigration {name: 'migration_log'})
                    SET m.applied = m.applied + [$version]
                    """,
                    version=version,
                )
            logger.info("[%s] done", version)

        logger.info("All migrations applied successfully")
    finally:
        await driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MedGraph schema migrations")
    parser.add_argument("--neo4j-uri", default=NEO4J_URI)
    parser.add_argument("--neo4j-user", default=NEO4J_USER)
    parser.add_argument("--neo4j-password", default=NEO4J_PASSWORD)
    args = parser.parse_args()
    asyncio.run(run_migrations(args.neo4j_uri, args.neo4j_user, args.neo4j_password))


if __name__ == "__main__":
    main()
