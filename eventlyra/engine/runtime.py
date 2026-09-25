"""Cola única de GPU. Las sesiones comparten las mismas instancias."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from eventlyra.engine.types import Cue, Transcript

logger = logging.getLogger(__name__)


def instance_id(obj: object) -> str:
    return f"{type(obj).__module__}.{type(obj).__qualname__}:{id(obj)}"


@dataclass
class ChunkJob:
    wav_path: Path
    offset: float
    source_lang: str
    target_lang: str
    is_current: Callable[[], bool]
    resolve_language: Callable[[], str | None]
    publish: Callable[[list[Cue], str | None, str | None], None]


class SharedRuntime:
    """Un reconocedor y un traductor para todas las sesiones del proceso."""

    def __init__(self, asr: object, translator: object) -> None:
        self.asr = asr
        self.translator = translator
        self._gpu = threading.Lock()
        self._queue: queue.Queue[ChunkJob | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._loop,
            name="eventlyra-gpu",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join(timeout=5)
        self._thread = None

    def submit(self, job: ChunkJob) -> None:
        self._queue.put(job)

    def _loop(self) -> None:
        while True:
            job = self._queue.get()
            try:
                if job is None:
                    return
                if not job.is_current():
                    continue
                try:
                    cues, detected = self._infer(job)
                    if job.is_current():
                        job.publish(cues, detected, None)
                except Exception as exc:
                    logger.exception("Falló un fragmento de audio")
                    try:
                        job.publish([], None, str(exc))
                    except Exception:
                        logger.exception("No se pudo publicar el error del fragmento")
            finally:
                if job is not None:
                    job.wav_path.unlink(missing_ok=True)
                self._queue.task_done()

    def _infer(self, job: ChunkJob) -> tuple[list[Cue], str]:
        language = job.resolve_language()
        with self._gpu:
            transcript: Transcript = self.asr.transcribe(job.wav_path, language)
            detected = transcript.language or language or "en"
            source = job.source_lang if job.source_lang != "auto" else detected
            cues: list[Cue] = []
            for segment in transcript.segments:
                text = segment.text.strip()
                if not text:
                    continue
                if source == job.target_lang:
                    translated = text
                else:
                    translated = self.translator.translate(text, source, job.target_lang)
                cues.append(
                    Cue(
                        start=job.offset + segment.start,
                        end=job.offset + max(segment.end, segment.start),
                        original=text,
                        translation=translated.strip(),
                        source_lang=source,
                        target_lang=job.target_lang,
                    )
                )
        return cues, detected
