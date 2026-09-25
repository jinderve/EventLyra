"""Cola única de GPU. Las sesiones se turnan; no se duplican los pesos."""

from __future__ import annotations

import logging
import threading
from collections import deque
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
    session_id: str = "1"
    langs: Callable[[], tuple[str, str]] | None = None

    def current_langs(self) -> tuple[str, str]:
        if self.langs is not None:
            return self.langs()
        return self.source_lang, self.target_lang


class SharedRuntime:
    """Un reconocedor y un traductor. La GPU atiende un fragmento a la vez, por turnos."""

    def __init__(self, asr: object, translator: object) -> None:
        self.asr = asr
        self.translator = translator
        self._gpu = threading.Lock()
        self._pending: dict[str, deque[ChunkJob]] = {}
        self._order: deque[str] = deque()
        self._cv = threading.Condition()
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(
            target=self._loop,
            name="eventlyra-gpu",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        self._thread.join(timeout=5)
        self._thread = None

    def submit(self, job: ChunkJob) -> None:
        sid = job.session_id
        with self._cv:
            if sid not in self._pending:
                self._pending[sid] = deque()
                self._order.append(sid)
            self._pending[sid].append(job)
            self._cv.notify()

    def _take(self) -> ChunkJob | None:
        with self._cv:
            while True:
                if self._stop and not any(self._pending.values()):
                    return None
                if not self._order:
                    if self._stop:
                        return None
                    self._cv.wait(timeout=0.2)
                    continue
                sid = self._order.popleft()
                cola = self._pending.get(sid)
                if not cola:
                    self._pending.pop(sid, None)
                    continue
                job = cola.popleft()
                if cola:
                    self._order.append(sid)
                else:
                    self._pending.pop(sid, None)
                return job

    def _loop(self) -> None:
        while True:
            job = self._take()
            if job is None:
                return
            try:
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
                job.wav_path.unlink(missing_ok=True)

    def _infer(self, job: ChunkJob) -> tuple[list[Cue], str]:
        source_sel, target = job.current_langs()
        language = None if source_sel == "auto" else source_sel
        with self._gpu:
            transcript: Transcript = self.asr.transcribe(job.wav_path, language)
            detected = transcript.language or language or "en"
            if detected not in {"es", "en"}:
                detected = "en"
            source = source_sel if source_sel != "auto" else detected
            cues: list[Cue] = []
            for segment in transcript.segments:
                if not job.is_current():
                    return [], detected
                text = segment.text.strip()
                if not text:
                    continue
                if source == target:
                    translated = text
                else:
                    translated = self.translator.translate(text, source, target)
                cues.append(
                    Cue(
                        start=job.offset + segment.start,
                        end=job.offset + max(segment.end, segment.start + 0.6),
                        original=text,
                        translation=translated.strip(),
                        source_lang=source,
                        target_lang=target,
                    )
                )
        return cues, detected
