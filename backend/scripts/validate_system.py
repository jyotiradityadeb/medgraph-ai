import asyncio
import sys

import httpx

BASE = "http://localhost:8000"


async def check(name: str, coro) -> tuple[bool, str]:
    _ = name
    try:
        result = await coro
        return True, str(result)
    except Exception as e:
        return False, str(e)


async def main():
    print("=" * 50)
    print("MedGraph AI — System Validation")
    print("=" * 50)

    qdrant_ok = False
    neo4j_ok = False

    async with httpx.AsyncClient(timeout=30) as client:
        # Health check
        ok, msg = await check("Backend health", client.get(BASE + "/health"))
        health_data = httpx.get(BASE + "/health").json() if ok else {}
        qdrant_ok = health_data.get("services", {}).get("qdrant", False)
        neo4j_ok = health_data.get("services", {}).get("neo4j", False)

        print(f"{'OK' if ok else 'FAIL'} Backend API: {'running' if ok else msg}")
        print(f"{'OK' if qdrant_ok else 'FAIL'} Qdrant vector DB")
        print(f"{'OK' if neo4j_ok else 'FAIL'} Neo4j graph DB")

        # Graph stats
        try:
            stats_resp = httpx.get(BASE + "/api/v1/graph/stats")
            stats = stats_resp.json()
            total_nodes = 0
            if isinstance(stats, dict):
                if isinstance(stats.get("node_counts_by_label"), list):
                    total_nodes = sum(
                        int(item.get("count", 0)) for item in stats["node_counts_by_label"]
                    )
                else:
                    total_nodes = sum(v for _, v in stats.items() if isinstance(v, int))
            print(f"OK Neo4j nodes: {total_nodes} total")
        except Exception:
            print("FAIL Could not fetch graph stats")

        # Graph explore
        try:
            explore_resp = httpx.get(BASE + "/api/v1/graph/explore?entity=Warfarin&depth=2")
            explore = explore_resp.json()
            print(
                f"OK Graph explore: {len(explore.get('nodes', []))} nodes returned for 'Warfarin'"
            )
        except Exception:
            print("FAIL Graph explore endpoint")

        # Query test (non-streaming)
        try:
            query_resp = httpx.post(
                BASE + "/api/v1/query",
                json={
                    "query": "What does aspirin treat?",
                    "modalities": ["text"],
                    "top_k": 3,
                    "use_graph": True,
                    "graph_depth": 1,
                    "model": "gpt-4o",
                },
                timeout=30,
            )
            if query_resp.status_code == 200:
                print("OK Query endpoint: streaming response started")
            else:
                print(f"FAIL Query endpoint: {query_resp.status_code}")
        except Exception as e:
            print(f"FAIL Query endpoint: {e}")

        # Ingest test
        try:
            ingest_resp = httpx.post(
                BASE + "/api/v1/ingest/text",
                json={
                    "content": "Test clinical note for validation: Patient presents with hypertension.",
                    "source": "validation_test",
                },
            )
            print(f"OK Ingest text: {ingest_resp.json().get('document_id', 'no id')[:8]}...")
        except Exception as e:
            print(f"FAIL Ingest: {e}")

        # Metrics
        try:
            metrics_resp = httpx.get(BASE + "/api/v1/metrics")
            metrics = metrics_resp.json()
            print(f"OK Metrics: {metrics.get('total_queries', 0)} queries processed")
        except Exception:
            print("FAIL Metrics endpoint")

    print()
    all_ok = qdrant_ok and neo4j_ok
    if all_ok:
        print("SYSTEM STATUS: READY FOR DEMO")
        sys.exit(0)
    else:
        print("SYSTEM STATUS: ISSUES DETECTED — fix before demo")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
