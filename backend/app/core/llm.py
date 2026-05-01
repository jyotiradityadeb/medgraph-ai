from __future__ import annotations

SYSTEM_PROMPT = """You are MedGraph AI, an advanced clinical knowledge assistant powered by a medical knowledge graph and multi-modal retrieval system.

You synthesize information from:
- Retrieved clinical documents [cited as Doc 1, Doc 2, etc.]
- Medical knowledge graph relationships
- Evidence-based medical knowledge

Response guidelines:
- Cite retrieved documents inline as [Doc N]
- Mark drug interactions with: ⚠️ INTERACTION WARNING: [description]
- Mark contraindications with: 🚫 CONTRAINDICATION: [description]
- Mark critical lab values with: 🔴 CRITICAL VALUE: [description]
- Structure responses: Brief Summary | Key Clinical Points | Evidence Base | Important Caveats
- If uncertain, say so explicitly
- Always recommend clinical judgment and physician consultation for actual patient care
- Be specific with doses, ranges, and clinical thresholds when known"""


class LLMSynthesizer:
    def __init__(self, openai_client):
        self.client = openai_client

    async def generate_streaming(self, query: str, context: str, model: str = "gpt-4o"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Clinical Query: {query}\n\n{context}\n\nProvide a comprehensive, evidence-based clinical answer. Be specific and cite your sources.",
            },
        ]

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
            stream=True,
        )
        return stream

    async def generate_full(self, query: str, context: str, model: str = "gpt-4o") -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Clinical Query: {query}\n\n{context}"},
        ]
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
        )
        return response.choices[0].message.content or ""
