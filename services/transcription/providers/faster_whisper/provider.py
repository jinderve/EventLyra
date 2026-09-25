"""faster-whisper turbo INT8 provider. One instance per process."""

from __future__ import annotations

import threading

from eventlyra.config import Settings
from services.live_engine.types import Transcript, TranscriptSegment

_LANGUAGES = {"es", "en", "pt"}

_SPANISH_MARKERS = (
    " qué ",
    " porque",
    " está ",
    " están ",
    " vamos a",
    " el que ",
    " también",
)

_PORTUGUESE_MARKERS = (
    "ção",
    "ções",
    " não ",
    " você ",
    " vocês ",
    "está a ",
    " para o ",
)


def looks_spanish(text: str) -> bool:
    lowered = f" {text.lower()} "
    if any(marker in lowered for marker in _SPANISH_MARKERS):
        return True
    return sum(ch in "áéíóúñü¿¡" for ch in lowered) >= 2


def looks_portuguese(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(marker in lowered for marker in _PORTUGUESE_MARKERS)


def resolve_detected_language(
    language: str | None,
    detected: str | None,
    probability: float,
    text: str,
) -> str:
    """Honor a fixed language and correct weak English auto-detection."""
    if language in _LANGUAGES:
        return language
    if looks_portuguese(text):
        return "pt"
    if looks_spanish(text):
        return "es"
    code = (detected or "").split("-")[0]
    if code in _LANGUAGES:
        return code
    return "en"


class FasterWhisperTurbo:
    """Wrap one WhisperModel shared by every logical session."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._load_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        with self._load_lock:
            if self._model is not None:
                return
            from faster_whisper import WhisperModel

            # No download_root: the cache follows HF_HOME and avoids duplication.
            self._model = WhisperModel(
                self.settings.whisper_model,
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
            )

    def transcribe(self, wav_path, language: str | None) -> Transcript:
        self.load()
        assert self._model is not None
        segments, info = self._model.transcribe(
            str(wav_path),
            language=language if language in _LANGUAGES else None,
            task="transcribe",
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
            multilingual=True,
        )
        collected = [
            TranscriptSegment(start=segment.start, end=segment.end, text=segment.text)
            for segment in segments
        ]
        joined = " ".join(item.text for item in collected)
        probability = float(getattr(info, "language_probability", 0.0) or 0.0)
        detected = resolve_detected_language(
            language,
            getattr(info, "language", None),
            probability,
            joined,
        )
        return Transcript(language=detected, segments=collected)


# Deprecated names retained for existing imports during the staged migration.
parece_espanol = looks_spanish
parece_portugues = looks_portuguese
idioma_de_info = resolve_detected_language
