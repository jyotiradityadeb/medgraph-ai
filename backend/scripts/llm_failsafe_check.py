from __future__ import annotations

import asyncio
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.llm import LLMSynthesizer, build_grounded_fallback_answer
from app.models.schemas import GraphContext, GraphEdge, GraphNode, Source


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message


@dataclass
class _Response:
    choices: list[_Choice]


class _FakeCompletionsRaise:
    async def create(self, *args, **kwargs):
        raise RuntimeError("synthetic llm failure")


class _FakeCompletionsEmpty:
    async def create(self, *args, **kwargs):
        return _Response(choices=[_Choice(message=_Message(content=""))])


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


def _assert_non_empty(label: str, value: str):
    ok = bool(value and value.strip())
    print(f"{'OK' if ok else 'FAIL'}  {label}")
    if not ok:
        raise AssertionError(f"{label}: answer is empty")


async def main():
    print("\nMedGraph LLM Fail-safe Check")
    print("=" * 40)

    query = "CYP2C9 and VKORC1 warfarin dosing in CKD"
    context = "=== RETRIEVED CLINICAL DOCUMENTS ===\n[1] Warfarin and CKD note"

    sources = [
        Source(
            id="doc_1",
            content="Warfarin dosing is influenced by CYP2C9 and VKORC1 variants; CKD may increase bleeding risk.",
            score=0.93,
            modality="text",
            metadata={},
        )
    ]
    graph_context = GraphContext(
        nodes=[
            GraphNode(id="drug_warfarin", label="Warfarin", type="Drug", properties={}),
            GraphNode(id="gene_cyp2c9", label="CYP2C9", type="Gene", properties={}),
        ],
        edges=[
            GraphEdge(
                source="drug_warfarin",
                target="gene_cyp2c9",
                relationship="METABOLIZED_BY",
                weight=1.0,
                properties={},
            )
        ],
        traversal_depth=2,
        entities_found=["Warfarin", "CYP2C9"],
    )

    # 1) OPENAI_API_KEY missing
    missing_key_synth = LLMSynthesizer(AsyncOpenAI(api_key=""))
    answer_missing = await missing_key_synth.generate_full(query, context)
    _assert_non_empty("OPENAI_API_KEY missing -> fallback answer", answer_missing)

    # 2) OPENAI_API_KEY invalid
    invalid_key_synth = LLMSynthesizer(AsyncOpenAI(api_key="invalid_key_for_demo_test"))
    answer_invalid = await invalid_key_synth.generate_full(query, context)
    _assert_non_empty("OPENAI_API_KEY invalid -> fallback answer", answer_invalid)

    # 3) OpenAI call raises exception
    raise_synth = LLMSynthesizer(_FakeClient(_FakeCompletionsRaise()))
    answer_raise = await raise_synth.generate_full(query, context)
    _assert_non_empty("Synthetic OpenAI exception -> fallback answer", answer_raise)

    # 4) OpenAI returns empty response
    empty_synth = LLMSynthesizer(_FakeClient(_FakeCompletionsEmpty()))
    answer_empty = await empty_synth.generate_full(query, context)
    _assert_non_empty("Empty LLM response -> fallback answer", answer_empty)

    # 5) Retrieval available, graph empty
    fallback_5 = build_grounded_fallback_answer(query, sources, {"nodes": [], "edges": []})
    _assert_non_empty("Retrieval available + graph empty", fallback_5)

    # 6) Graph available, retrieval empty
    fallback_6 = build_grounded_fallback_answer(query, [], graph_context.model_dump())
    _assert_non_empty("Graph available + retrieval empty", fallback_6)

    # 7) Retrieval and graph available
    fallback_7 = build_grounded_fallback_answer(query, sources, graph_context.model_dump())
    _assert_non_empty("Retrieval available + graph available", fallback_7)

    print("=" * 40)
    print("Result: all fail-safe checks passed")


if __name__ == "__main__":
    asyncio.run(main())
