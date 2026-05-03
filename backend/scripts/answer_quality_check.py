from __future__ import annotations

import asyncio
import json
import os
import re

import httpx

QUERY = "CYP2C9 and VKORC1 warfarin dosing in CKD"
REQUIRED_HEADINGS = [
    "## Clinical Interpretation",
    "## Retrieved Evidence",
    "## Graph-Grounded Evidence",
    "## Practical Caution",
]


def _assert(condition: bool, label: str):
    print(f"{'OK' if condition else 'FAIL'}  {label}")
    if not condition:
        raise AssertionError(label)


def _extract_section(answer: str, heading: str) -> str:
    pattern = rf"{re.escape(heading)}\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, answer, flags=re.DOTALL)
    return (match.group(1).strip() if match else "").strip()


async def run_query_check(expect_fallback: bool):
    payload = {
        "query": QUERY,
        "modalities": ["text"],
        "top_k": 5,
        "use_graph": True,
        "graph_depth": 2,
    }
    metadata = {}
    done_event = {}
    answer = ""
    saw_error_event = False

    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream("POST", "http://localhost:8000/api/v1/query", json=payload) as resp:
            _assert(resp.status_code == 200, "HTTP 200 from query endpoint")
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except Exception:
                    continue
                event_type = event.get("type")
                if event_type == "metadata":
                    metadata = event
                elif event_type == "chunk":
                    answer += str(event.get("content", ""))
                elif event_type == "done":
                    done_event = event
                    break
                elif event_type == "error":
                    saw_error_event = True

    _assert(not saw_error_event, "No error SSE event emitted")
    _assert(bool(answer.strip()), "Non-empty streamed answer")
    for heading in REQUIRED_HEADINGS:
        _assert(heading in answer, f"Answer contains heading: {heading}")

    retrieved_block = _extract_section(answer, "## Retrieved Evidence")
    _assert(bool(retrieved_block), "Retrieved Evidence section is present and non-empty")
    _assert(
        "- " in retrieved_block or "[" in retrieved_block,
        "Retrieved Evidence section includes at least one evidence item",
    )

    graph_block = _extract_section(answer, "## Graph-Grounded Evidence")
    _assert(bool(graph_block), "Graph-Grounded Evidence section is present and non-empty")

    graph_context = done_event.get("graph_context", {}) if isinstance(done_event, dict) else {}
    nodes_count = len(graph_context.get("nodes", []) or [])
    rel_count = len(graph_context.get("relationships", []) or [])
    _assert(nodes_count > 0, "Graph context remains populated (nodes > 0)")

    if rel_count > 0:
        _assert(
            "not available for this query" not in graph_block.lower(),
            "Graph section uses available relationship evidence when relationships exist",
        )

    llm_status = str(metadata.get("llm_status", "")).strip().lower()
    _assert(llm_status in {"ok", "fallback"}, "llm_status is ok or fallback")
    if expect_fallback:
        _assert(llm_status == "fallback", "llm_status is fallback for invalid/missing key")


async def main():
    print("\nMedGraph Answer Quality Check")
    print("=" * 40)
    key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    expect_fallback = (not key) or key.startswith("invalid_key_for_demo_test")
    await run_query_check(expect_fallback=expect_fallback)
    print("=" * 40)
    print("Result: answer quality checks passed")


if __name__ == "__main__":
    asyncio.run(main())
