"""faster-whisper turbo en INT8. Una instancia por proceso."""

from __future__ import annotations

import threading

from eventlyra.config import Settings
from eventlyra.engine.types import Transcript, TranscriptSegment

_MARCAS_ES = (
    " qué ",
    " porque",
    " está ",
    " están ",
    " vamos a",
    " el que ",
    " también",
)


def parece_espanol(texto: str) -> bool:
    bajo = f" {texto.lower()} "
    if any(marca in bajo for marca in _MARCAS_ES):
        return True
    return sum(ch in "áéíóúñü¿¡" for ch in bajo) >= 2


def idioma_de_info(language: str | None, detectado: str | None, probabilidad: float, texto: str) -> str:
    """Si el caller fijó es/en, manda. En auto, no nos quedamos con un 'en' flojo."""
    if language in {"es", "en"}:
        return language
    if parece_espanol(texto):
        return "es"
    code = (detectado or "").split("-")[0]
    if code in {"es", "en"}:
        return code
    return "en"


class FasterWhisperTurbo:
    """Envuelve un único WhisperModel compartido por todas las sesiones."""

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

            # Sin download_root: el caché respeta HF_HOME y no duplica el repo.
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
            language=language if language in {"es", "en"} else None,
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
        probabilidad = float(getattr(info, "language_probability", 0.0) or 0.0)
        detectado = idioma_de_info(
            language,
            getattr(info, "language", None),
            probabilidad,
            joined,
        )
        return Transcript(language=detectado, segments=collected)
