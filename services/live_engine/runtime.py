"""Single GPU queue. Sessions take turns and never duplicate model weights."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from services.live_engine.glossary import apply_glossary
from services.live_engine.types import Cue, Transcript

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
    queued_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    submitted_at: float = field(default_factory=time.monotonic)

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
        self._last_error: str | None = None
        self._last_latency_ms: int | None = None
        self._last_queue_wait_ms: int | None = None
        self._last_cue_at: float | None = None

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

    def snapshot(self) -> dict:
        with self._cv:
            queues = {sid: len(queue) for sid, queue in self._pending.items()}
        return {
            "queue_by_session": queues,
            "cola_por_sesion": queues,
            "queue_total": sum(queues.values()),
            "last_error": self._last_error,
            "last_latency_ms": self._last_latency_ms,
            "last_queue_wait_ms": self._last_queue_wait_ms,
            "last_cue_at": self._last_cue_at,
        }

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
                queue = self._pending.get(sid)
                if not queue:
                    self._pending.pop(sid, None)
                    continue
                job = queue.popleft()
                job.started_at = time.monotonic()
                if queue:
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
                        self._last_error = None
                        job.publish(cues, detected, None)
                except Exception as exc:
                    logger.exception("Falló un fragmento de audio")
                    self._last_error = str(exc)
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
            if detected not in {"es", "en", "pt"}:
                detected = "en"
            source = source_sel if source_sel != "auto" else detected
            cues: list[Cue] = []
            started = job.started_at or time.monotonic()
            queued = job.queued_at or job.submitted_at
            queue_wait_ms = max(0, int((started - queued) * 1000))
            for segment in transcript.segments:
                if not job.is_current():
                    return [], detected
                text = apply_glossary(segment.text.strip())
                if not text:
                    continue
                if source == target:
                    translated = text
                else:
                    translated = apply_glossary(
                        self.translator.translate(text, source, target)
                    )
                latency_ms = int((time.monotonic() - started) * 1000)
                cues.append(
                    Cue(
                        start=job.offset + segment.start,
                        end=job.offset + max(segment.end, segment.start + 0.6),
                        original=text,
                        translation=translated.strip(),
                        source_lang=source,
                        target_lang=target,
                        latency_ms=latency_ms,
                        queue_wait_ms=queue_wait_ms,
                    )
                )
            infer_ms = int((time.monotonic() - started) * 1000)
            self._last_latency_ms = infer_ms
            self._last_queue_wait_ms = queue_wait_ms
            self._last_cue_at = time.time()
        return cues, detected
