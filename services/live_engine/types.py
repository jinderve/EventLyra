"""Types shared by audio, transcription, translation, and realtime delivery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    language: str
    segments: list[TranscriptSegment]


@dataclass
class Cue:
    start: float
    end: float
    original: str
    translation: str
    source_lang: str
    target_lang: str
    index: int = 0
    generation: int = 0
    latency_ms: int | None = None
    queue_wait_ms: int | None = None

    def to_dict(self) -> dict:
        data = {
            "index": self.index,
            "generation": self.generation,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "original": self.original,
            "translation": self.translation,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "latency_ms": self.latency_ms,
            "queue_wait_ms": self.queue_wait_ms,
        }
        # Temporary aliases for the existing vanilla client.
        data.update(
            {
                "indice": data["index"],
                "generacion": data["generation"],
                "inicio": data["start"],
                "fin": data["end"],
                "traduccion": data["translation"],
                "idioma_origen": data["source_lang"],
                "idioma_destino": data["target_lang"],
                "latencia_ms": data["latency_ms"],
                "espera_cola_ms": data["queue_wait_ms"],
            }
        )
        return data
