"""Ingest DrugBank Open Data CSV into the MedGraph Neo4j knowledge graph.

DrugBank Open Data is freely available for academic use:
  https://go.drugbank.com/releases/latest#open-data

Usage:
  python -m scripts.ingest_drugbank_open [--csv PATH] [--interactions PATH]

Defaults: downloads drugbank_open_structures.csv to /tmp if not provided.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import logging
import sys
import urllib.request
from pathlib import Path

from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_STRUCTURES_URL = "https://go.drugbank.com/releases/latest/downloads/all-open-drugbank-structures"
_DDI_URL = "https://go.drugbank.com/releases/latest/downloads/all-open-drugbank-interactions"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "changeme"


async def upsert_drug(session, row: dict) -> str | None:
    drug_id = (row.get("DrugBank ID") or row.get("drugbank_id") or "").strip()
    name = (row.get("Name") or row.get("name") or "").strip()
    smiles = (row.get("SMILES") or row.get("smiles") or "").strip()
    inchikey = (row.get("InChIKey") or row.get("inchikey") or "").strip()

    if not drug_id or not name:
        return None

    await session.run(
        """
        MERGE (d:Drug {id: $drug_id})
        SET d.name = $name,
            d.smiles = $smiles,
            d.inchikey = $inchikey,
            d.source = 'drugbank_open'
        """,
        drug_id=drug_id,
        name=name,
        smiles=smiles,
        inchikey=inchikey,
    )
    return drug_id


async def upsert_interaction(session, row: dict) -> None:
    drug1_id = (row.get("Drug1 DrugBank ID") or row.get("drug1_drugbank_id") or "").strip()
    drug2_id = (row.get("Drug2 DrugBank ID") or row.get("drug2_drugbank_id") or "").strip()
    description = (row.get("Description") or row.get("description") or "").strip()

    if not drug1_id or not drug2_id:
        return

    await session.run(
        """
        MATCH (d1:Drug {id: $drug1_id}), (d2:Drug {id: $drug2_id})
        MERGE (d1)-[r:INTERACTS_WITH]->(d2)
        SET r.description = $description, r.source = 'drugbank_open'
        """,
        drug1_id=drug1_id,
        drug2_id=drug2_id,
        description=description[:500] if description else "",
    )


def _read_csv(path_or_bytes: str | bytes) -> list[dict]:
    if isinstance(path_or_bytes, bytes):
        text = path_or_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
    else:
        reader = csv.DictReader(open(path_or_bytes, encoding="utf-8"))
    return list(reader)


def _download(url: str) -> bytes:
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


async def run(structures_path: str | None, interactions_path: str | None) -> None:
    if structures_path:
        structures_data = structures_path
    else:
        try:
            structures_data = _download(_STRUCTURES_URL)
        except Exception as exc:
            logger.error("Failed to download structures: %s", exc)
            sys.exit(1)

    rows = _read_csv(structures_data)
    logger.info("Loaded %d drug structure records", len(rows))

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        async with driver.session() as session:
            upserted = 0
            for row in rows:
                drug_id = await upsert_drug(session, row)
                if drug_id:
                    upserted += 1
                if upserted % 100 == 0:
                    logger.info("Upserted %d drugs...", upserted)
            logger.info("Drug upsert complete: %d drugs", upserted)

            if interactions_path:
                interactions_data = interactions_path
            else:
                try:
                    interactions_data = _download(_DDI_URL)
                except Exception as exc:
                    logger.warning("Interactions download failed (skipping): %s", exc)
                    interactions_data = None

            if interactions_data:
                ddi_rows = _read_csv(interactions_data)
                logger.info("Loaded %d drug-drug interaction records", len(ddi_rows))
                for row in ddi_rows:
                    await upsert_interaction(session, row)
                logger.info("DDI upsert complete")

    finally:
        await driver.close()

    logger.info("DrugBank Open Data ingestion complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest DrugBank Open Data into MedGraph Neo4j")
    parser.add_argument("--csv", help="Path to drugbank_open_structures.csv (downloads if omitted)")
    parser.add_argument("--interactions", help="Path to drug-drug interactions CSV")
    parser.add_argument("--neo4j-uri", default=NEO4J_URI)
    parser.add_argument("--neo4j-user", default=NEO4J_USER)
    parser.add_argument("--neo4j-password", default=NEO4J_PASSWORD)
    args = parser.parse_args()

    global NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    NEO4J_URI = args.neo4j_uri
    NEO4J_USER = args.neo4j_user
    NEO4J_PASSWORD = args.neo4j_password

    asyncio.run(run(args.csv, args.interactions))


if __name__ == "__main__":
    main()
