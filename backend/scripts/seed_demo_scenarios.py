from __future__ import annotations

import asyncio

import httpx
from openai import AsyncOpenAI

import app.db.qdrant_client as qdrant_module
from app.config import get_settings
from app.core.multimodal import MultiModalIngestPipeline
from app.db.qdrant_client import QdrantService

SCENARIO_NOTES = [
    {
        "id": "demo_1",
        "title": "Complex polypharmacy patient",
        "content": """CLINICAL NOTE - Internal Medicine Consult

Patient: 72-year-old male
PMH: Type 2 Diabetes Mellitus (HbA1c 7.8%), Hypertension (BP 142/88), Atrial Fibrillation (chronic)
Current Medications:
- Warfarin 5mg daily (INR target 2.0-3.0, last INR 2.4)
- Metformin 1000mg twice daily
- Lisinopril 10mg daily
- Metoprolol succinate 50mg daily

New Problem: Community-acquired pneumonia confirmed on chest X-ray
Proposed treatment: Clarithromycin 500mg twice daily x 7 days

PHARMACIST CONCERN: Multiple drug interactions identified with clarithromycin addition.
Clarithromycin is a potent CYP3A4 and CYP2D6 inhibitor.

Lab values: Serum creatinine 1.3 mg/dL, eGFR 58 mL/min/1.73m², Potassium 4.2 mEq/L, INR 2.4

Clinical question: What are the clinically significant drug interactions with clarithromycin in this patient and how should we manage them?""",
        "lab_values": {"HbA1c": 7.8, "eGFR": 58, "INR": 2.4, "potassium": 4.2, "creatinine": 1.3},
    },
    {
        "id": "demo_2",
        "title": "Complex lab interpretation",
        "content": """LAB RESULT NOTIFICATION - Critical Values

Patient: 68-year-old female with known heart failure, T2DM, CKD

LABORATORY RESULTS:
HbA1c: 8.9% (H) - Reference: <5.7% normal, 5.7-6.4% prediabetes, >=6.5% diabetes
Fasting glucose: 187 mg/dL (H) - Reference: 70-99 mg/dL
BNP (B-type natriuretic peptide): 450 pg/mL (H) - Reference: <100 pg/mL
Troponin I: 0.06 ng/mL (H) - Reference: <0.04 ng/mL
eGFR: 52 mL/min/1.73m² - Reference: >60 normal; Stage G3a CKD
Urine albumin-creatinine ratio: 85 mg/g (H) - Reference: <30 mg/g
Potassium: 4.8 mEq/L - Reference: 3.5-5.0 mEq/L
LDL cholesterol: 118 mg/dL - Reference: <100 mg/dL optimal
TSH: 2.1 mIU/L - Reference: 0.4-4.0 mIU/L (normal)""",
        "lab_values": {
            "HbA1c": 8.9,
            "fasting_glucose": 187,
            "BNP": 450,
            "troponin": 0.06,
            "eGFR": 52,
            "potassium": 4.8,
            "ldl": 118,
        },
    },
    {
        "id": "demo_3",
        "title": "Dyspnea differential diagnosis",
        "content": """ED TRIAGE NOTE

Chief Complaint: Worsening shortness of breath x 3 weeks

HPI: 60-year-old male, former smoker (40 pack-years, quit 5 years ago), presenting with 3 weeks of progressive exertional dyspnea now present at rest. He reports sleeping on 3 pillows (orthopnea), waking up at night gasping (PND). Bilateral ankle swelling worsening over 2 weeks. Significant fatigue. Denies fever, productive cough, chest pain, or syncope.

PMH: Hypertension x 15 years (poorly controlled per patient), hyperlipidemia. No prior cardiac history. No hospitalizations.

Medications: Amlodipine 10mg daily (patient reports inconsistent use)

Vitals: BP 168/102, HR 96, RR 22, SpO2 92% on room air, Temp 37.2°C
Weight: 84 kg (baseline ~78 kg 1 month ago — 6kg weight gain)

Physical Exam: JVD present at 45 degrees, bibasilar crackles, S3 gallop, 2+ pitting edema bilateral lower extremities to knees""",
        "lab_values": {
            "BNP": 820,
            "troponin": 0.03,
            "sodium": 134,
            "potassium": 3.8,
            "creatinine": 1.6,
            "eGFR": 42,
        },
    },
    {
        "id": "demo_4",
        "title": "T2DM treatment protocol",
        "content": """PRIMARY CARE NOTE - New Patient Visit

Patient: 45-year-old male, newly diagnosed Type 2 Diabetes Mellitus
HbA1c at diagnosis: 8.5%
Weight: 94 kg, BMI 31.2 (obese class I)
BP: 134/82 mmHg
eGFR: 78 mL/min/1.73m² (normal)
No cardiovascular disease, no heart failure, no CKD
LDL: 142 mg/dL

Family history: Father with T2DM, MI at age 62
Lifestyle: Sedentary desk job, high carbohydrate diet, no regular exercise

The patient asks: What is the best treatment approach? What medications should I start? What lifestyle changes matter most? Will I need insulin?""",
        "lab_values": {"HbA1c": 8.5, "fasting_glucose": 196, "ldl": 142, "eGFR": 78, "BMI": 31.2},
    },
    {
        "id": "demo_5",
        "title": "Furosemide mechanism and monitoring",
        "content": """PHARMACOLOGY EDUCATION NOTE

Resident question regarding furosemide (Lasix) pharmacology:

A 72-year-old male with decompensated heart failure is started on IV furosemide 80mg twice daily. The attending asks the resident to explain:
1. The mechanism of action of furosemide
2. Why furosemide causes hypokalemia specifically
3. What electrolytes and parameters need monitoring
4. When to be concerned about ototoxicity

Patient labs before starting furosemide:
Potassium: 4.1 mEq/L, Sodium: 138 mEq/L, Creatinine 1.4 mg/dL, eGFR 48
BNP: 1240 pg/mL, Weight 88 kg (dry weight estimated 82 kg)""",
        "lab_values": {"potassium": 4.1, "sodium": 138, "creatinine": 1.4, "eGFR": 48, "BNP": 1240},
    },
    {
        "id": "demo_6",
        "title": "CYP2C9 pharmacogenomics and warfarin",
        "content": """PHARMACOGENOMICS CONSULT NOTE

Patient referred for warfarin dosing difficulty.
68-year-old female with AF, multiple dose adjustments needed to achieve therapeutic INR.
Current warfarin: 7.5mg daily (higher than average dose of 5mg)
Current INR: 1.7 (subtherapeutic, target 2.0-3.0)
No bleeding episodes. No interacting medications identified.

Pharmacogenomic testing ordered:
CYP2C9 genotype: *1/*1 (normal metabolizer — NOT the cause)
VKORC1 genotype: GG at position 1639 (low sensitivity — explains higher dose requirement)
CYP4F2 genotype: CC (normal)

Concurrent diseases: Atrial fibrillation (indication for warfarin), Hypertension (on amlodipine), CKD stage 2 (eGFR 68)

Clinical question: How do genetic variants CYP2C9 and VKORC1 affect warfarin dosing? How does CKD affect anticoagulation management?""",
        "lab_values": {"INR": 1.7, "eGFR": 68, "creatinine": 1.1, "potassium": 4.3},
    },
]


async def main() -> None:
    settings = get_settings()
    service = QdrantService(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    qdrant_module.qdrant_service = service
    await service.initialize()

    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    pipeline = MultiModalIngestPipeline(openai_client)

    notes_count = 0
    tables_count = 0

    print("Seeding demo scenarios...")
    for idx, scenario in enumerate(SCENARIO_NOTES, start=1):
        print(f"[{idx}/6] {scenario['title']}")
        note_id, entities = await pipeline.ingest_text(
            scenario["content"],
            source=f"demo://{scenario['id']}",
            metadata={"scenario_id": scenario["id"], "scenario_title": scenario["title"]},
        )
        notes_count += 1
        print(f"  - note ingested: {note_id} (entities={len(entities)})")

        table_id, abnormal = await pipeline.ingest_lab_table(
            scenario["lab_values"],
            metadata={"scenario_id": scenario["id"], "scenario_title": scenario["title"]},
        )
        tables_count += 1
        print(f"  - labs ingested: {table_id} (abnormal={len(abnormal)})")

    # Pre-warm query cache via the running API service.
    print("Pre-warming query cache...")
    warm_queries = [
        "Warfarin interactions in elderly patients with AF",
        "Interpret: HbA1c 8.9%, BNP 450, eGFR 52",
        "Differential diagnosis: dyspnea + orthopnea + edema",
        "First-line treatment for T2DM with HbA1c 8.5%",
        "How does furosemide cause hypokalemia?",
        "CYP2C9 and VKORC1 warfarin dosing in CKD",
    ]
    async with httpx.AsyncClient(timeout=45) as client:
        for warm_query in warm_queries:
            try:
                await client.post(
                    "http://localhost:8000/api/v1/query",
                    json={
                        "query": warm_query,
                        "modalities": ["text", "table"],
                        "top_k": 5,
                        "use_graph": True,
                        "graph_depth": 2,
                        "model": "gpt-4o",
                    },
                )
                print(f"  - warmed: {warm_query[:48]}...")
            except Exception as exc:
                print(f"  - cache warm failed for query '{warm_query[:32]}...': {exc}")

    print()
    print("Demo scenarios seeded:")
    print(f"- {notes_count} clinical notes ingested")
    print(f"- {tables_count} lab tables ingested")
    print("- Medical knowledge graph: already seeded from seed_graph.py")
    print("- System ready for demo queries")


if __name__ == "__main__":
    asyncio.run(main())
