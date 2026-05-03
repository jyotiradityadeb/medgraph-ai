import sys
import time

import httpx

BASE = "http://localhost:8000"


def check(label, fn):
    try:
        result = fn()
        print(f"  OK  {label}")
        return True
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return False


def run():
    print("\nMedGraph AI — Demo Readiness Check\n" + "=" * 40)
    results = []

    # Flow 1: Health
    results.append(
        check(
            "Backend health",
            lambda: httpx.get(f"{BASE}/health", timeout=5).raise_for_status(),
        )
    )

    # Flow 2: Ingest text
    results.append(
        check(
            "Ingest clinical note",
            lambda: httpx.post(
                f"{BASE}/api/v1/ingest/text",
                json={"content": "Patient with warfarin and AF.", "source": "demo_check"},
                timeout=30,
            ).raise_for_status(),
        )
    )

    # Flow 3: Graph explore
    results.append(
        check(
            "Graph explore (Warfarin)",
            lambda: httpx.get(
                f"{BASE}/api/v1/graph/explore?entity=Warfarin&depth=1",
                timeout=10,
            ).raise_for_status(),
        )
    )

    # Flow 4: Graph search
    results.append(
        check(
            "Graph search (warfarin)",
            lambda: httpx.get(
                f"{BASE}/api/v1/graph/search?q=warfarin",
                timeout=10,
            ).raise_for_status(),
        )
    )

    # Flow 5: Query endpoint reachable
    results.append(
        check(
            "Query endpoint reachable",
            lambda: httpx.post(
                f"{BASE}/api/v1/query",
                json={
                    "query": "aspirin uses",
                    "modalities": ["text"],
                    "top_k": 2,
                    "use_graph": True,
                    "graph_depth": 1,
                    "model": "gpt-4o",
                },
                timeout=5,
            ),
        )
    )  # just check it starts, not full response

    # Flow 6: Metrics
    results.append(
        check(
            "Metrics endpoint",
            lambda: httpx.get(f"{BASE}/api/v1/metrics", timeout=5).raise_for_status(),
        )
    )

    # Flow 7: Lab ingest
    results.append(
        check(
            "Ingest lab values",
            lambda: httpx.post(
                f"{BASE}/api/v1/ingest/table",
                json={"lab_values": {"HbA1c": 8.5, "eGFR": 55}, "patient_id": "demo"},
                timeout=15,
            ).raise_for_status(),
        )
    )

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 40}")
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print("STATUS: DEMO READY")
    elif passed >= 5:
        print("STATUS: MOSTLY READY — fix failing checks before demo")
    else:
        print("STATUS: NOT READY — run docker-compose up -d and make seed first")

    return 0 if passed >= 5 else 1


if __name__ == "__main__":
    sys.exit(run())
