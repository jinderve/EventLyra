"""faster-whisper turbo en INT8. Una instancia por proceso."""

from __future__ import annotations

import threading

from eventlyra.config import Settings
from eventlyra.engine.types import Transcript, TranscriptSegment


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
            language=language,
            task="transcribe",
            vad_filter=True,
            beam_size=5,
        )
        detected = (info.language or language or "en").split("-")[0]
        collected = [
            TranscriptSegment(start=segment.start, end=segment.end, text=segment.text)
            for segment in segments
        ]
        return Transcript(language=detected, segments=collected)
