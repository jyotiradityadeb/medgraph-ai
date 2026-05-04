from __future__ import annotations

import re
from typing import Any

import structlog
from openai import APIError, APITimeoutError, AuthenticationError, RateLimitError

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are MedGraph AI, a clinical assistant that must stay grounded in provided retrieval and graph context only.

Hard requirements:
- Use only the provided context from retrieval and graph evidence.
- Do not claim access to external databases or unseen patient data.
- Avoid unsupported or overconfident claims; state uncertainty when evidence is incomplete.
- Keep the answer concise, clinically useful, and demo-friendly.
- Include a brief safety caution and avoid presenting this as medical advice.
- Structure output exactly with these markdown headings:
## Clinical Interpretation
## Retrieved Evidence
## Graph-Grounded Evidence
## Practical Caution
"""

_MEDICAL_SIGNAL_TERMS = {
    "warfarin",
    "aspirin",
    "metformin",
    "furosemide",
    "lisinopril",
    "cyp2c9",
    "vkorc1",
    "ckd",
    "chronic kidney disease",
    "diabetes",
    "hba1c",
    "inr",
    "egfr",
    "dosing",
    "dose",
    "genotype",
    "variant",
    "contraindication",
    "interaction",
    "adverse",
    "bleeding",
    "risk",
    "renal",
    "kidney",
    "hypokalemia",
}

_RELATIONSHIP_TEXT = {
    "METABOLIZED_BY": "is connected to {target} through metabolism-related evidence.",
    "AFFECTS_METABOLISM_OF": "is connected to {target} through metabolism-effect evidence.",
    "INFLUENCES_DOSING_OF": "is connected to {target} through pharmacogenomic dosing evidence.",
    "INTERACTS_WITH": "is connected to {target} through interaction evidence.",
    "CONTRAINDICATED_IN": "is linked to caution in {target}.",
    "TREATS": "is linked to treatment evidence for {target}.",
    "ASSOCIATED_WITH": "is associated with {target} in the graph evidence.",
    "INCREASES_RISK_OF": "is connected to increased risk evidence for {target}.",
    "DECREASES_RISK_OF": "is connected to reduced risk evidence for {target}.",
    "CAUSES": "is connected to adverse-effect evidence involving {target}.",
}


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _extract_query_entities(query: str) -> set[str]:
    lowered = query.lower()
    tokens = set(_tokenize(query))
    entities = {token for token in tokens if len(token) >= 3}
    for phrase in [
        "chronic kidney disease",
        "atrial fibrillation",
        "type 2 diabetes mellitus",
        "heart failure",
        "peripheral edema",
    ]:
        if phrase in lowered:
            entities.add(phrase)
    return entities


def _humanize_entity(name: str) -> str:
    raw = _safe_str(name).replace("_", " ")
    if not raw:
        return "Unknown"
    parts = raw.split()
    if len(parts) > 1 and parts[0].lower() in {
        "drug",
        "gene",
        "disease",
        "symptom",
        "lab",
        "condition",
        "variant",
        "doc",
    }:
        raw = " ".join(parts[1:])
    words = []
    for token in raw.split():
        if re.fullmatch(r"[A-Z0-9\-]+", token):
            words.append(token)
        elif re.fullmatch(r"[a-z]{1,6}\d+[a-z0-9]*", token):
            words.append(token.upper())
        else:
            words.append(token.capitalize())
    return " ".join(words) if words else raw


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_text(text: str) -> str:
    return " ".join(_safe_str(text).split())


def _parse_chunk(chunk: Any) -> dict[str, Any]:
    if chunk is None:
        return {"id": "", "content": "", "score": 0.0, "modality": "text"}
    if isinstance(chunk, dict):
        return {
            "id": _safe_str(chunk.get("id", "")),
            "content": _safe_str(chunk.get("content", "")),
            "score": _coerce_float(chunk.get("score", 0.0)),
            "modality": _safe_str(chunk.get("modality", "text")) or "text",
        }
    return {
        "id": _safe_str(getattr(chunk, "id", "")),
        "content": _safe_str(getattr(chunk, "content", "")),
        "score": _coerce_float(getattr(chunk, "score", 0.0)),
        "modality": _safe_str(getattr(chunk, "modality", "text")) or "text",
    }


def _score_chunk_for_query(chunk: dict[str, Any], query_entities: set[str]) -> float:
    content = chunk.get("content", "")
    lowered = content.lower()
    score = _coerce_float(chunk.get("score", 0.0))
    for entity in query_entities:
        if entity and entity in lowered:
            score += 2.0
    signal_hits = 0
    for term in _MEDICAL_SIGNAL_TERMS:
        if term in lowered:
            signal_hits += 1
    score += min(signal_hits * 0.35, 2.0)
    if "dose" in lowered or "dosing" in lowered:
        score += 0.6
    if "contra" in lowered or "caution" in lowered:
        score += 0.5
    if "risk" in lowered or "adverse" in lowered:
        score += 0.5
    return score


def _rank_retrieved_chunks(query: str, retrieved_chunks: list[Any]) -> list[dict[str, Any]]:
    query_entities = _extract_query_entities(query)
    ranked: list[tuple[float, dict[str, Any]]] = []
    seen: set[str] = set()
    for item in retrieved_chunks:
        parsed = _parse_chunk(item)
        content = _normalize_text(parsed.get("content", ""))
        if not content:
            continue
        dedupe_key = content[:220].lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        parsed["content"] = content
        ranked.append((_score_chunk_for_query(parsed, query_entities), parsed))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in ranked[:5]]


def extract_graph_relationships(graph_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    graph = graph_context or {}
    rel_items = graph.get("relationships", []) or []
    if not rel_items:
        rel_items = graph.get("edges", []) or []
    for raw in rel_items:
        if not isinstance(raw, dict):
            continue
        source = _safe_str(raw.get("source", ""))
        target = _safe_str(raw.get("target", ""))
        relationship = _safe_str(raw.get("relationship", ""))
        if not source or not target or not relationship:
            continue
        properties = raw.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        relationships.append(
            {
                "source": source,
                "target": target,
                "relationship": relationship,
                "properties": properties,
            }
        )
    return relationships


def _score_relationship(query: str, relationship: dict[str, Any], query_entities: set[str]) -> float:
    src = _safe_str(relationship.get("source", ""))
    tgt = _safe_str(relationship.get("target", ""))
    rel = _safe_str(relationship.get("relationship", ""))
    src_l, tgt_l, rel_l = src.lower(), tgt.lower(), rel.lower()
    query_l = query.lower()
    score = 0.0
    if src_l in query_l:
        score += 3.0
    if tgt_l in query_l:
        score += 3.0
    for entity in query_entities:
        if entity in src_l:
            score += 1.5
        if entity in tgt_l:
            score += 1.5
        if entity in rel_l:
            score += 1.0
    for keyword in [
        "metabol",
        "dosing",
        "genom",
        "contra",
        "risk",
        "adverse",
        "interact",
        "caution",
    ]:
        if keyword in rel_l:
            score += 0.8
    return score


def rank_graph_relationships(query: str, relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_entities = _extract_query_entities(query)
    ranked: list[tuple[float, dict[str, Any]]] = []
    seen: set[tuple[str, str, str]] = set()
    for rel in relationships:
        key = (
            _safe_str(rel.get("source", "")).lower(),
            _safe_str(rel.get("target", "")).lower(),
            _safe_str(rel.get("relationship", "")).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        ranked.append((_score_relationship(query, rel, query_entities), rel))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [rel for _, rel in ranked[:8]]


def _relationship_to_sentence(relationship: dict[str, Any]) -> str:
    source = _humanize_entity(_safe_str(relationship.get("source", "")))
    target = _humanize_entity(_safe_str(relationship.get("target", "")))
    rel = _safe_str(relationship.get("relationship", "")).upper()
    template = _RELATIONSHIP_TEXT.get(rel)
    if template:
        return f"{source} {template.format(target=target)}"
    rel_words = rel.replace("_", " ").lower().strip()
    return f"{source} is connected to {target} through {rel_words} evidence."


def _relationship_why_it_matters(relationship: dict[str, Any]) -> str:
    rel = _safe_str(relationship.get("relationship", "")).lower()
    if any(token in rel for token in ["metabol", "genom", "dosing"]):
        return "This may affect dose selection and monitoring intensity."
    if any(token in rel for token in ["contra", "risk", "adverse", "cause"]):
        return "This highlights potential safety risk and supports careful clinical review."
    if any(token in rel for token in ["interact"]):
        return "This supports interaction screening before medication decisions."
    return "This relationship provides additional clinical context for decision support."


def format_graph_evidence(relationships: list[dict[str, Any]]) -> str:
    if not relationships:
        return "- Graph evidence was not available for this query."
    lines = []
    for rel in relationships[:6]:
        sentence = _relationship_to_sentence(rel)
        why = _relationship_why_it_matters(rel)
        lines.append(f"- {sentence} {why}")
    return "\n".join(lines)


def build_grounded_fallback_answer(
    query: str, retrieved_chunks: list[object] | None, graph_context: dict[str, object] | None
) -> str:
    """Build a deterministic, non-throwing fallback answer from retrieval + graph evidence."""
    try:
        ranked_chunks = _rank_retrieved_chunks(query, list(retrieved_chunks or []))
        relationships = extract_graph_relationships(graph_context)
        ranked_relationships = rank_graph_relationships(query, relationships)
        graph_nodes_count = len((graph_context or {}).get("nodes", []) or [])

        if ranked_chunks:
            evidence_lines = []
            for chunk in ranked_chunks[:5]:
                src_id = chunk.get("id") or "retrieved_source"
                modality = _safe_str(chunk.get("modality", "text")).upper()
                snippet = _safe_str(chunk.get("content", ""))[:240]
                evidence_lines.append(f"- [{src_id}] ({modality}) {snippet}")
            retrieved_evidence_block = "\n".join(evidence_lines)
        else:
            retrieved_evidence_block = (
                "- Retrieved evidence was limited for this query; interpretation is conservative."
            )

        if ranked_relationships:
            graph_block = (
                f"- Graph context included {graph_nodes_count} nodes with relationship evidence.\n"
                + format_graph_evidence(ranked_relationships)
            )
        else:
            graph_block = "- Graph evidence was not available for this query."

        lowered_query = query.lower()
        interpretation = (
            "Based on retrieved medical context and graph evidence, this query suggests clinically relevant "
            "links between treatment choice, pharmacogenomics, and risk-modifying comorbid factors."
        )
        if "warfarin" in lowered_query:
            interpretation = (
                "Based on retrieved medical context and graph evidence, warfarin-related decisions should "
                "emphasize individualized dosing, interaction awareness, and close INR-guided monitoring."
            )
        if "aspirin" in lowered_query and "warfarin" in lowered_query:
            interpretation = (
                "Aspirin with warfarin is associated with increased bleeding risk because antiplatelet and "
                "anticoagulant effects can be additive. Management typically requires INR and bleeding-sign "
                "monitoring, and the combination should not be adjusted without clinician supervision."
            )

        return (
            "Evidence-grounded clinical synthesis\n\n"
            "## Clinical Interpretation\n"
            f"{interpretation}\n\n"
            "## Retrieved Evidence\n"
            f"{retrieved_evidence_block}\n\n"
            "## Graph-Grounded Evidence\n"
            f"{graph_block}\n\n"
            "## Practical Caution\n"
            "- This response is for informational support and is not medical advice.\n"
            "- Final clinical decisions require clinician review of patient context and current guidelines.\n"
            "- Dosing, pharmacogenomic interpretation, and CKD-related adjustments need professional oversight.\n"
            "- For aspirin plus warfarin, avoid unsupervised combination or dose changes; clinician review is required."
        )
    except Exception as exc:
        logger.warning("fallback_answer_generation_failed", error=str(exc), exc_info=True)
        return (
            "Evidence-grounded clinical synthesis\n\n"
            "## Clinical Interpretation\n"
            "A grounded fallback response is provided, but evidence summarization was partially limited.\n\n"
            "## Retrieved Evidence\n"
            "- Retrieved evidence could not be fully summarized in this pass.\n\n"
            "## Graph-Grounded Evidence\n"
            "- Graph evidence could not be fully summarized in this pass.\n\n"
            "## Practical Caution\n"
            "- This response is not medical advice; clinician review is required."
        )


def _build_fallback_answer(
    query: str,
    context: str,
    retrieved_chunks: list[object] | None = None,
    graph_context: dict[str, object] | None = None,
) -> dict[str, str]:
    if retrieved_chunks is not None or graph_context is not None:
        answer = build_grounded_fallback_answer(query, retrieved_chunks or [], graph_context or {})
    else:
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        doc_lines = [line for line in lines if line.startswith("[") and "]" in line][:3]
        rel_lines = [line for line in lines if "--[" in line and "]-->" in line][:5]
        retrieved_block = (
            "\n".join(f"- {line[:220]}" for line in doc_lines)
            if doc_lines
            else "- Retrieved evidence was limited for this query."
        )
        graph_block = (
            "\n".join(f"- {line}" for line in rel_lines)
            if rel_lines
            else "- Graph evidence was not available for this query."
        )
        answer = (
            "Evidence-grounded clinical synthesis\n\n"
            "## Clinical Interpretation\n"
            "A deterministic grounded summary was generated from available context.\n\n"
            "## Retrieved Evidence\n"
            f"{retrieved_block}\n\n"
            "## Graph-Grounded Evidence\n"
            f"{graph_block}\n\n"
            "## Practical Caution\n"
            "- This response is not medical advice; clinician review is required."
        )
    return {"answer": answer, "mode": "fallback", "reason": "AI synthesis fallback mode"}


class _FallbackDelta:
    def __init__(self, content: str):
        self.content = content


class _FallbackChoice:
    def __init__(self, content: str):
        self.delta = _FallbackDelta(content)


class _FallbackChunk:
    def __init__(self, content: str):
        self.choices = [_FallbackChoice(content)]


def _parse_cited_doc_ids(answer: str) -> list[str]:
    return re.findall(r"\[Doc\s+(\d+)\]", answer)


def _check_answer_grounding(
    answer: str,
    sources: list[Any],
    graph_context: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    cited_ids = _parse_cited_doc_ids(answer)
    cited_sources: list[str] = []
    for raw_id in cited_ids:
        idx = int(raw_id) - 1
        if 0 <= idx < len(sources):
            source = sources[idx]
            src_id = _safe_str(getattr(source, "id", None) or (source.get("id") if isinstance(source, dict) else None))
            if src_id:
                cited_sources.append(src_id)

    graph = graph_context or {}
    node_labels = {
        _safe_str(n.get("label", "")).lower()
        for n in (graph.get("nodes") or [])
        if isinstance(n, dict)
    }
    answer_lower = answer.lower()
    source_texts = " ".join(
        _safe_str(getattr(s, "content", None) or (s.get("content") if isinstance(s, dict) else "")).lower()
        for s in sources
    )

    _DRUG_RE = re.compile(
        r"\b(warfarin|aspirin|metformin|furosemide|lisinopril|atorvastatin|amlodipine|"
        r"digoxin|amiodarone|vancomycin|ciprofloxacin|amoxicillin|azithromycin|doxycycline|"
        r"sertraline|escitalopram|quetiapine|lithium|haloperidol|clopidogrel|rivaroxaban|"
        r"apixaban|dabigatran|heparin|insulin|metoprolol|losartan|ramipril|omeprazole|"
        r"spironolactone|carvedilol)\b",
        re.IGNORECASE,
    )
    mentioned_drugs = {m.group(0).lower() for m in _DRUG_RE.finditer(answer)}
    ungrounded = [
        d for d in mentioned_drugs
        if d not in source_texts and d not in node_labels
    ]
    if ungrounded:
        logger.warning("hallucination_guard.ungrounded_drugs", drugs=ungrounded)
        grounding_check = "warning"
    else:
        grounding_check = "passed"

    return grounding_check, cited_sources


class LLMSynthesizer:
    def __init__(self, openai_client):
        self.client = openai_client

    def build_fallback_payload(
        self,
        query: str,
        context: str,
        retrieved_chunks: list[object] | None = None,
        graph_context: dict[str, object] | None = None,
    ) -> dict[str, str]:
        return _build_fallback_answer(query, context, retrieved_chunks, graph_context)

    async def generate_streaming(
        self,
        query: str,
        context: str,
        model: str = "gpt-4o",
        retrieved_chunks: list[object] | None = None,
        graph_context: dict[str, object] | None = None,
    ):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Clinical Query: {query}\n\n"
                    f"{context}\n\n"
                    "Respond using only the provided retrieval and graph context. "
                    "Do not fabricate evidence. Keep the response concise. "
                    "Use exactly these sections:\n"
                    "## Clinical Interpretation\n"
                    "## Retrieved Evidence\n"
                    "## Graph-Grounded Evidence\n"
                    "## Practical Caution"
                ),
            },
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
                stream=True,
            )
            return {"stream": stream, "mode": "live", "reason": "", "llm_status": "ok"}
        except (AuthenticationError, APIError, RateLimitError, APITimeoutError, TimeoutError) as exc:
            logger.warning("llm_streaming_openai_fallback", error=str(exc), model=model, exc_info=True)
            fallback_payload = self.build_fallback_payload(
                query, context, retrieved_chunks, graph_context
            )

            async def fallback_stream():
                for line in fallback_payload["answer"].splitlines():
                    yield _FallbackChunk(f"{line}\n")

            return {
                "stream": fallback_stream(),
                "mode": fallback_payload["mode"],
                "reason": fallback_payload["reason"],
                "llm_status": "fallback",
            }
        except Exception as exc:
            logger.warning("llm_streaming_failed_fallback", error=str(exc), model=model, exc_info=True)
            fallback_payload = self.build_fallback_payload(
                query, context, retrieved_chunks, graph_context
            )

            async def fallback_stream():
                for line in fallback_payload["answer"].splitlines():
                    yield _FallbackChunk(f"{line}\n")

            return {
                "stream": fallback_stream(),
                "mode": fallback_payload["mode"],
                "reason": fallback_payload["reason"],
                "llm_status": "fallback",
            }

    async def generate_full(self, query: str, context: str, model: str = "gpt-4o") -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Clinical Query: {query}\n\n{context}\n\n"
                    "Respond with the required four sections only, grounded strictly in provided evidence."
                ),
            },
        ]
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
            answer = (response.choices[0].message.content or "").strip()
            if answer:
                return answer
            logger.warning("llm_full_empty_response_fallback", model=model)
            return self.build_fallback_payload(query, context)["answer"]
        except (AuthenticationError, APIError, RateLimitError, APITimeoutError, TimeoutError) as exc:
            logger.warning("llm_full_openai_fallback", error=str(exc), model=model, exc_info=True)
            return self.build_fallback_payload(query, context)["answer"]
        except Exception as exc:
            logger.warning("llm_full_failed_fallback", error=str(exc), model=model, exc_info=True)
            return self.build_fallback_payload(query, context)["answer"]
