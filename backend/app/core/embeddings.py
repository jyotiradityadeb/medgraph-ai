from __future__ import annotations

import base64
import hashlib
import io
from typing import Any

import numpy as np
import structlog
from openai import AsyncOpenAI
from PIL import Image

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    from transformers import CLIPModel, CLIPProcessor
except Exception:
    CLIPModel = None
    CLIPProcessor = None

logger = structlog.get_logger()


def fallback_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.zeros(384, dtype=float)
    for i in range(384):
        arr[i] = digest[i % len(digest)] / 255.0
    norm = np.linalg.norm(arr)
    return (arr / norm).tolist() if norm else arr.tolist()


class TextEmbedder:
    _model = None
    _model_load_attempted = False
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def get_model(cls):
        if cls._model is None and not cls._model_load_attempted:
            cls._model_load_attempted = True
            if SentenceTransformer is None:
                logger.warning("sentence_transformers_unavailable_fallback")
                return None
            try:
                cls._model = SentenceTransformer(cls.MODEL_NAME)
            except Exception as exc:
                logger.warning("sentence_transformers_load_failed_fallback", error=str(exc))
                cls._model = None
        return cls._model

    def embed(self, text: str) -> list[float]:
        cleaned = text.strip().replace("\n", " ")[: 512 * 4]
        model = self.get_model()
        if model is None:
            return fallback_embedding(cleaned)
        try:
            embedding = model.encode(cleaned, normalize_embeddings=True)
            if isinstance(embedding, np.ndarray):
                return embedding.tolist()
            return list(embedding)
        except Exception as exc:
            logger.warning("text_embedding_failed_fallback", error=str(exc))
            return fallback_embedding(cleaned)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.strip().replace("\n", " ")[: 512 * 4] for t in texts]
        model = self.get_model()
        if model is None:
            return [fallback_embedding(t) for t in cleaned]
        try:
            embeddings = model.encode(
                cleaned, normalize_embeddings=True, batch_size=16, show_progress_bar=False
            )
            if isinstance(embeddings, np.ndarray):
                return embeddings.tolist()
            return [list(vec) for vec in embeddings]
        except Exception as exc:
            logger.warning("text_batch_embedding_failed_fallback", error=str(exc))
            return [fallback_embedding(t) for t in cleaned]

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
    _model_load_attempted = False
    MODEL_NAME = "openai/clip-vit-base-patch32"

    @classmethod
    def get_model(cls):
        if cls._model is None and not cls._model_load_attempted:
            cls._model_load_attempted = True
            if CLIPModel is None or CLIPProcessor is None:
                logger.warning("clip_unavailable_fallback")
                return None, None
            try:
                cls._processor = CLIPProcessor.from_pretrained(cls.MODEL_NAME)
                cls._model = CLIPModel.from_pretrained(cls.MODEL_NAME)
            except Exception as exc:
                logger.warning("clip_load_failed_fallback", error=str(exc))
                cls._model = None
                cls._processor = None
        return cls._model, cls._processor

    def embed_image(self, image_bytes: bytes) -> list[float]:
        model, processor = self.get_model()
        if model is None or processor is None:
            image_key = hashlib.sha256(image_bytes).hexdigest()
            return fallback_embedding(f"image:{image_key}")
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt", padding=True)
            try:
                import torch
            except Exception:
                return fallback_embedding(hashlib.sha256(image_bytes).hexdigest())

            with torch.no_grad():
                features = model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            return features[0].tolist()
        except Exception as exc:
            logger.warning("image_embedding_failed_fallback", error=str(exc))
            image_key = hashlib.sha256(image_bytes).hexdigest()
            return fallback_embedding(f"image:{image_key}")

    def embed_text_for_image_search(self, text: str) -> list[float]:
        model, processor = self.get_model()
        if model is None or processor is None:
            return fallback_embedding(text)
        try:
            inputs = processor(text=[text], return_tensors="pt", padding=True)
            try:
                import torch
            except Exception:
                return fallback_embedding(text)

            with torch.no_grad():
                features = model.get_text_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            return features[0].tolist()
        except Exception as exc:
            logger.warning("image_text_embedding_failed_fallback", error=str(exc))
            return fallback_embedding(text)

    async def generate_description(self, image_bytes: bytes, openai_client: AsyncOpenAI) -> str:
        if CLIPModel is None or CLIPProcessor is None:
            return (
                "Medical image uploaded. Demo fallback description mode is active; "
                "advanced visual model dependencies are unavailable."
            )
        try:
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
        except Exception as exc:
            logger.warning("image_description_failed", error=str(exc))
            return (
                "Medical image uploaded. Visual analysis temporarily unavailable. "
                "Image has been embedded for similarity search."
            )


class AudioTranscriber:
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.text_embedder = TextEmbedder()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> dict[str, Any]:
        try:
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
        except Exception as exc:
            logger.warning("audio_transcription_failed", error=str(exc))
            return {
                "transcript": (
                    "Audio received. Demo fallback transcription mode is active; "
                    "returning placeholder transcript."
                ),
                "duration": 0,
                "language": "en",
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
