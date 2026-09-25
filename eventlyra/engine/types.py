"""Tipos que cruzan el motor de audio, la transcripción y la traducción."""

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

    def to_dict(self) -> dict:
        return {
            "indice": self.index,
            "generacion": self.generation,
            "inicio": round(self.start, 3),
            "fin": round(self.end, 3),
            "original": self.original,
            "traduccion": self.translation,
            "idioma_origen": self.source_lang,
            "idioma_destino": self.target_lang,
        }
