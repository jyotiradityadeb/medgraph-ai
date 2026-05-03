"""Evaluation harness for MedGraph AI query pipeline.

Run: python -m scripts.eval_pipeline
Exit code 1 if pass rate < 80%.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from typing import Any

API_BASE = "http://localhost:8000"

GOLDEN: list[dict[str, Any]] = [
    {
        "query": "Warfarin interactions in elderly patients with atrial fibrillation",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Warfarin", "Atrial Fibrillation"],
        "expected_keywords": ["clinical interpretation", "interaction"],
    },
    {
        "query": "Interpret HbA1c 8.9% in type 2 diabetes patient",
        "expected_intent": "lab_interpretation",
        "expected_entities": ["HbA1c", "Type 2 Diabetes Mellitus"],
        "expected_keywords": ["clinical interpretation", "hba1c"],
    },
    {
        "query": "Differential diagnosis for dyspnea orthopnea and edema",
        "expected_intent": "diagnosis",
        "expected_entities": ["Dyspnea", "Orthopnea"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Metformin safety in CKD stage 3b",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Metformin", "Chronic Kidney Disease"],
        "expected_keywords": ["clinical interpretation", "renal", "kidney"],
    },
    {
        "query": "First-line treatment for type 2 diabetes with HbA1c 8.5%",
        "expected_intent": "treatment",
        "expected_entities": ["Type 2 Diabetes Mellitus", "HbA1c"],
        "expected_keywords": ["clinical interpretation", "treatment"],
    },
    {
        "query": "How does furosemide cause hypokalemia",
        "expected_intent": "pharmacology",
        "expected_entities": ["Furosemide", "Hypokalemia"],
        "expected_keywords": ["clinical interpretation", "potassium"],
    },
    {
        "query": "Warfarin dosing with CYP2C9 poor metabolizer genotype",
        "expected_intent": "pharmacology",
        "expected_entities": ["Warfarin", "CYP2C9"],
        "expected_keywords": ["clinical interpretation", "dose"],
    },
    {
        "query": "Lisinopril contraindications in pregnancy",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Lisinopril"],
        "expected_keywords": ["clinical interpretation", "contraindication"],
    },
    {
        "query": "Interpret eGFR 38 creatinine 2.1 in elderly patient",
        "expected_intent": "lab_interpretation",
        "expected_entities": ["eGFR", "Creatinine"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "BNP 850 in patient with dyspnea and edema",
        "expected_intent": "lab_interpretation",
        "expected_entities": ["BNP", "Dyspnea"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Aspirin antiplatelet mechanism and bleeding risk",
        "expected_intent": "pharmacology",
        "expected_entities": ["Aspirin"],
        "expected_keywords": ["clinical interpretation", "risk"],
    },
    {
        "query": "Atorvastatin myopathy risk with CYP3A4 inhibitors",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Atorvastatin", "CYP3A4"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Amiodarone and warfarin drug interaction mechanism",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Amiodarone", "Warfarin"],
        "expected_keywords": ["clinical interpretation", "interaction"],
    },
    {
        "query": "Potassium 5.9 in CKD patient on spironolactone",
        "expected_intent": "lab_interpretation",
        "expected_entities": ["Chronic Kidney Disease", "Spironolactone"],
        "expected_keywords": ["clinical interpretation", "potassium"],
    },
    {
        "query": "INR 4.2 on warfarin what action to take",
        "expected_intent": "lab_interpretation",
        "expected_entities": ["INR", "Warfarin"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Hypothyroidism management with TSH 12 on levothyroxine",
        "expected_intent": "treatment",
        "expected_entities": ["Hypothyroidism", "TSH"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Heart failure treatment with reduced ejection fraction",
        "expected_intent": "treatment",
        "expected_entities": ["Heart Failure"],
        "expected_keywords": ["clinical interpretation", "treatment"],
    },
    {
        "query": "Digoxin toxicity signs and management",
        "expected_intent": "pharmacology",
        "expected_entities": ["Digoxin"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Ciprofloxacin and QT prolongation risk",
        "expected_intent": "drug_interaction",
        "expected_entities": ["Ciprofloxacin"],
        "expected_keywords": ["clinical interpretation"],
    },
    {
        "query": "Atrial fibrillation rate control with beta blockers",
        "expected_intent": "treatment",
        "expected_entities": ["Atrial Fibrillation"],
        "expected_keywords": ["clinical interpretation", "rate"],
    },
]


def _stream_query(query: str) -> dict[str, Any]:
    payload = json.dumps({
        "query": query,
        "modalities": ["text"],
        "top_k": 5,
        "use_graph": True,
        "graph_depth": 2,
        "model": "gpt-4o",
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/api/v1/query",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    result: dict[str, Any] = {"answer": "", "metadata": {}, "done": {}}
    with urllib.request.urlopen(req, timeout=60) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = json.loads(line[5:].strip())
            event_type = data.get("type")
            if event_type == "metadata":
                result["metadata"] = data
            elif event_type == "chunk":
                result["answer"] += data.get("content", "")
            elif event_type == "done":
                result["done"] = data
    return result


def _eval_case(case: dict[str, Any]) -> tuple[bool, str]:
    query = case["query"]
    try:
        res = _stream_query(query)
    except Exception as exc:
        return False, f"request failed: {exc}"

    metadata = res.get("metadata", {})
    answer_lower = res.get("answer", "").lower()

    intent = metadata.get("intent", "")
    if intent != case["expected_intent"]:
        return False, f"intent={intent!r} expected={case['expected_intent']!r}"

    for kw in case["expected_keywords"]:
        if kw.lower() not in answer_lower:
            return False, f"missing keyword {kw!r}"

    return True, "ok"


def main() -> None:
    print(f"Running {len(GOLDEN)} eval cases against {API_BASE}\n")
    passed = 0
    failed = 0
    for i, case in enumerate(GOLDEN, 1):
        t0 = time.time()
        ok, reason = _eval_case(case)
        elapsed = round(time.time() - t0, 1)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{i:02d}] {status} ({elapsed}s) {case['query'][:60]}")
        if not ok:
            print(f"       reason: {reason}")

    total = passed + failed
    pass_rate = passed / total if total else 0
    print(f"\nResult: {passed}/{total} passed ({pass_rate:.0%})")

    if pass_rate < 0.80:
        print("FAIL: pass rate below 80% threshold")
        sys.exit(1)
    print("PASS: eval threshold met")


if __name__ == "__main__":
    main()
