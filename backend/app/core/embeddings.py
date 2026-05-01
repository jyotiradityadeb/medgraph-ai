from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
from openai import AsyncOpenAI
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor


class TextEmbedder:
    _model = None
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer(cls.MODEL_NAME)
        return cls._model

    def embed(self, text: str) -> list[float]:
        model = self.get_model()
        cleaned = text.strip().replace("\n", " ")[: 512 * 4]
        embedding = model.encode(cleaned, normalize_embeddings=True)
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return list(embedding)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self.get_model()
        cleaned = [t.strip().replace("\n", " ")[: 512 * 4] for t in texts]
        embeddings = model.encode(
            cleaned, normalize_embeddings=True, batch_size=16, show_progress_bar=False
        )
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [list(vec) for vec in embeddings]

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks if chunks else [text]


class ImageEmbedder:
    _model = None
    _processor = None
    MODEL_NAME = "openai/clip-vit-base-patch32"

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._processor = CLIPProcessor.from_pretrained(cls.MODEL_NAME)
            cls._model = CLIPModel.from_pretrained(cls.MODEL_NAME)
        return cls._model, cls._processor

    def embed_image(self, image_bytes: bytes) -> list[float]:
        model, processor = self.get_model()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = processor(images=image, return_tensors="pt", padding=True)
        import torch

        with torch.no_grad():
            features = model.get_image_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].tolist()

    def embed_text_for_image_search(self, text: str) -> list[float]:
        model, processor = self.get_model()
        inputs = processor(text=[text], return_tensors="pt", padding=True)
        import torch

        with torch.no_grad():
            features = model.get_text_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].tolist()

    async def generate_description(self, image_bytes: bytes, openai_client: AsyncOpenAI) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": "Describe this medical image clinically. State the imaging modality (X-ray, CT, MRI, ultrasound, etc.), anatomical region, any abnormal findings, and clinical significance in 3-5 sentences.",
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content or ""


class AudioTranscriber:
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.text_embedder = TextEmbedder()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
        )
        return {
            "transcript": transcript.text,
            "duration": getattr(transcript, "duration", 0),
            "language": getattr(transcript, "language", "en"),
        }

    def embed_transcript(self, transcript: str) -> list[float]:
        return self.text_embedder.embed(transcript)


NORMAL_RANGES = {
    "hba1c": (4.0, 5.7, "%"),
    "fasting_glucose": (70, 99, "mg/dL"),
    "bnp": (0, 100, "pg/mL"),
    "troponin": (0, 0.04, "ng/mL"),
    "tsh": (0.4, 4.0, "mIU/L"),
    "free_t4": (0.8, 1.8, "ng/dL"),
    "inr": (0.8, 1.2, "ratio"),
    "egfr": (60, 999, "mL/min/1.73m²"),
    "ldl": (0, 100, "mg/dL"),
    "potassium": (3.5, 5.0, "mEq/L"),
    "sodium": (136, 145, "mEq/L"),
    "creatinine": (0.6, 1.2, "mg/dL"),
}


class TableEmbedder:
    def __init__(self):
        self.text_embedder = TextEmbedder()

    def embed_lab_values(self, labs: dict[str, float]) -> tuple[list[float], list[dict[str, Any]]]:
        parts = []
        abnormal: list[dict[str, Any]] = []
        for key, value in labs.items():
            key_lower = key.lower().replace(" ", "_").replace("/", "_")
            if key_lower in NORMAL_RANGES:
                low, high, unit = NORMAL_RANGES[key_lower]
                status = "normal"
                if value < low:
                    status = "LOW"
                    abnormal.append(
                        {
                            "test": key,
                            "value": value,
                            "unit": unit,
                            "status": "LOW",
                            "normal": f"{low}-{high}",
                        }
                    )
                elif value > high:
                    status = "HIGH"
                    abnormal.append(
                        {
                            "test": key,
                            "value": value,
                            "unit": unit,
                            "status": "HIGH",
                            "normal": f"{low}-{high}",
                        }
                    )
                parts.append(f"{key}: {value} {unit} ({status})")
            else:
                parts.append(f"{key}: {value}")
        text = "Laboratory results: " + ". ".join(parts)
        return self.text_embedder.embed(text), abnormal


class EmbeddingService(TextEmbedder):
    def __init__(self, settings: Any | None = None):
        self.settings = settings

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embed_batch(texts)
