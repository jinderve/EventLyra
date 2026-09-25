"""Arma los trabajos de una sesión a partir de un WAV ya normalizado."""

from __future__ import annotations

from pathlib import Path

from eventlyra.config import Settings
from eventlyra.engine.audio import chunk_wav
from eventlyra.engine.runtime import ChunkJob, SharedRuntime
from eventlyra.engine.sessions import Session
from eventlyra.engine.types import Cue


def enqueue_wav(
    session: Session,
    wav_path: Path,
    settings: Settings,
    runtime: SharedRuntime,
    generation: int,
    base_offset: float = 0.0,
) -> int:
    chunk_dir = wav_path.parent / "fragmentos"
    pieces = chunk_wav(wav_path, chunk_dir, settings.chunk_seconds, settings.sample_rate)
    submitted: set[Path] = set()
    try:
        with session.lock:
            if generation != session.generation:
                return 0
            source_lang = session.source_lang
            target_lang = session.target_lang
            session.pending += len(pieces)
            session.status = "procesando" if pieces else "lista"
            session.cond.notify_all()
        for offset, path, _duration in pieces:
            runtime.submit(
                _job(
                    session=session,
                    wav_path=path,
                    offset=base_offset + offset,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    generation=generation,
                )
            )
            submitted.add(path)
        return len(pieces)
    finally:
        wav_path.unlink(missing_ok=True)
        for _, path, _ in pieces:
            if path not in submitted:
                path.unlink(missing_ok=True)


def _job(
    session: Session,
    wav_path: Path,
    offset: float,
    source_lang: str,
    target_lang: str,
    generation: int,
) -> ChunkJob:
    def is_current() -> bool:
        with session.lock:
            return generation == session.generation

    def resolve_language() -> str | None:
        with session.lock:
            if source_lang != "auto":
                return source_lang
            return session.detected_lang

    def publish(cues: list[Cue], detected: str | None, error: str | None) -> None:
        with session.lock:
            if generation != session.generation:
                return
            if detected and source_lang == "auto" and session.detected_lang is None:
                session.detected_lang = detected
            if error:
                session.error = error
                session.status = "error"
            else:
                for cue in cues:
                    session.next_index += 1
                    cue.index = session.next_index
                    cue.generation = generation
                session.cues.extend(cues)
                session.cues.sort(key=lambda item: (item.start, item.index))
            session.pending -= 1
            if session.pending <= 0 and session.status != "error":
                session.status = "lista"
            session.cond.notify_all()

    return ChunkJob(
        wav_path=wav_path,
        offset=offset,
        source_lang=source_lang,
        target_lang=target_lang,
        is_current=is_current,
        resolve_language=resolve_language,
        publish=publish,
    )
