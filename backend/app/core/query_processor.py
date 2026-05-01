from __future__ import annotations

import json
from typing import Any

ABBREVIATION_MAP = {
    "HTN": "hypertension",
    "DM": "diabetes mellitus",
    "T2DM": "type 2 diabetes",
    "CAD": "coronary artery disease",
    "CHF": "congestive heart failure",
    "COPD": "chronic obstructive pulmonary disease",
    "MI": "myocardial infarction",
    "AF": "atrial fibrillation",
    "AFib": "atrial fibrillation",
    "CKD": "chronic kidney disease",
    "HbA1c": "glycated hemoglobin",
    "BNP": "brain natriuretic peptide",
    "eGFR": "estimated glomerular filtration rate",
    "LDL": "low density lipoprotein cholesterol",
    "TSH": "thyroid stimulating hormone",
    "INR": "international normalized ratio",
    "BP": "blood pressure",
    "HR": "heart rate",
    "RR": "respiratory rate",
    "SpO2": "oxygen saturation",
    "SOB": "shortness of breath",
    "DOE": "dyspnea on exertion",
    "PMH": "past medical history",
    "HF": "heart failure",
    "EF": "ejection fraction",
}


class QueryProcessor:
    def __init__(self, openai_client):
        self.client = openai_client

    def expand_abbreviations(self, query: str) -> str:
        words = query.split()
        expanded = []
        for word in words:
            clean = word.strip(".,;:")
            if clean in ABBREVIATION_MAP:
                expanded.append(ABBREVIATION_MAP[clean] + word[len(clean) :])
            else:
                expanded.append(word)
        return " ".join(expanded)

    async def classify_intent(self, query: str) -> dict[str, Any]:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical query classifier. Analyze the query and return a JSON object with:
- intent: one of "drug_interaction", "diagnosis", "treatment", "lab_interpretation", "symptom_lookup", "pharmacology", "general"
- relevant_modalities: list of "text", "image", "audio", "table" that would help answer
- extracted_entities: {"drugs": [], "diseases": [], "symptoms": [], "genes": [], "lab_tests": []}
- complexity: "simple" (1 entity, direct answer) | "multi_hop" (requires graph traversal) | "complex" (multiple conditions)
- requires_graph: boolean, true if relationship traversal would help
Return only valid JSON.""",
                },
                {"role": "user", "content": f"Classify this medical query: {query}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    def build_retrieval_queries(self, query: str, intent_result: dict[str, Any]) -> dict[str, Any]:
        entities = intent_result.get("extracted_entities", {})
        entity_terms = []
        for _, value in entities.items():
            if isinstance(value, list):
                entity_terms.extend(value)

        return {
            "text_query": query,
            "image_query": " ".join(entity_terms) + " medical imaging" if entity_terms else query,
            "table_query": " ".join(entities.get("lab_tests", [])) + " " + query,
            "graph_entities": entity_terms,
            "intent": intent_result.get("intent", "general"),
            "requires_graph": intent_result.get("requires_graph", True),
        }
