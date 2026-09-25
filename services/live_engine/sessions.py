"""Logical sessions. They hold state and captions, never model weights."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

from services.live_engine.types import Cue

SOURCE_LANGUAGES = {"auto", "es", "en", "pt"}
TARGET_LANGUAGES = {"es", "en", "pt"}
# Legacy imports remain until the vanilla UI is retired.
ORIGENES = SOURCE_LANGUAGES
DESTINOS = TARGET_LANGUAGES


@dataclass
class Session:
    id: str
    source_lang: str = "auto"
    target_lang: str = "es"
    status: str = "ready"
    pending: int = 0
    error: str | None = None
    detected_lang: str | None = None
    generation: int = 0
    next_index: int = 0
    last_latency_ms: int | None = None
    last_queue_wait_ms: int | None = None
    last_cue_at: float | None = None
    title: str | None = None
    room: str | None = None
    agenda_lang: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    image_url: str | None = None
    youtube_url: str | None = None
    track: str | None = None
    talk_id: str | None = None
    watchers: int = 0
    playback_kind: str | None = None
    playback_path: Path | None = None
    playback_url: str | None = None
    playback_content_type: str | None = None
    youtube_id: str | None = None
    youtube_is_live: bool = False
    stream_origin_at: float | None = None
    live_chunk_seconds: float | None = None
    cues: list[Cue] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    cond: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self.cond = threading.Condition(self.lock)

    def begin(self, status: str = "preparing") -> int:
        with self.lock:
            self.generation += 1
            self.cues.clear()
            self.pending = 0
            self.error = None
            self.detected_lang = None
            self.next_index = 0
            self.last_latency_ms = None
            self.last_queue_wait_ms = None
            self.last_cue_at = None
            self.playback_kind = None
            self.playback_path = None
            self.playback_url = None
            self.playback_content_type = None
            self.youtube_id = None
            self.youtube_is_live = False
            self.stream_origin_at = None
            self.live_chunk_seconds = None
            self.status = status
            self.cond.notify_all()
            return self.generation

    def fail_if_current(self, generation: int, message: str) -> None:
        with self.lock:
            if generation != self.generation:
                return
            self.error = message
            self.status = "error"
            self.pending = 0
            self.cond.notify_all()

    def add_watcher(self) -> None:
        with self.lock:
            self.watchers += 1

    def remove_watcher(self) -> None:
        with self.lock:
            self.watchers = max(0, self.watchers - 1)

    def apply_talk(self, talk: dict) -> None:
        source = talk.get("source_lang") or "auto"
        target = talk.get("target_lang") or "es"
        if source in SOURCE_LANGUAGES and target in TARGET_LANGUAGES:
            self.set_languages(source, target)
        with self.lock:
            self.talk_id = str(talk.get("id") or "") or None
            self.title = talk.get("title") or self.title
            self.room = talk.get("room")
            self.agenda_lang = talk.get("language") or talk.get("source_lang")
            self.description = talk.get("description")
            self.tags = list(talk.get("tags") or [])
            self.speakers = list(talk.get("speakers") or [])
            self.image_url = talk.get("image_url")
            self.youtube_url = talk.get("youtube_url")
            self.track = talk.get("track")

    def set_meta(
        self,
        *,
        title: str | None = None,
        room: str | None = None,
    ) -> None:
        with self.lock:
            if title is not None:
                cleaned = title.strip()
                self.title = cleaned or self.title
            if room is not None:
                cleaned_room = room.strip()
                self.room = cleaned_room or None

    def set_playback(
        self,
        *,
        kind: str,
        path: Path | None = None,
        url: str | None = None,
        content_type: str | None = None,
        youtube_id: str | None = None,
        is_live: bool | None = None,
    ) -> None:
        with self.lock:
            self.playback_kind = kind
            self.playback_path = path
            self.playback_url = url
            self.playback_content_type = content_type
            self.youtube_id = youtube_id
            if is_live is not None:
                self.youtube_is_live = is_live

    def configure_live(self, chunk_seconds: float) -> None:
        with self.lock:
            self.live_chunk_seconds = chunk_seconds
            self.youtube_is_live = True
            self.cond.notify_all()

    def configure_stream(self, chunk_seconds: float) -> None:
        with self.lock:
            self.live_chunk_seconds = chunk_seconds
            self.cond.notify_all()

    def ready_until(self) -> float:
        if not self.cues:
            return 0.0
        return max(cue.end for cue in self.cues)

    def mark_live_origin(self, origin_at: float, chunk_seconds: float) -> None:
        with self.lock:
            if self.stream_origin_at is None:
                self.stream_origin_at = origin_at
            self.live_chunk_seconds = chunk_seconds
            self.youtube_is_live = True
            self.cond.notify_all()

    def playback_delay_sec(self) -> float:
        chunk = self.live_chunk_seconds or 0.0
        infer = 4.0 if self.last_latency_ms is None else self.last_latency_ms / 1000
        wait = 0.0 if self.last_queue_wait_ms is None else self.last_queue_wait_ms / 1000
        return round(max(chunk + infer + wait + 0.8, chunk + 1.0), 2)

    def set_languages(self, source_lang: str, target_lang: str) -> None:
        if source_lang not in SOURCE_LANGUAGES:
            raise ValueError("Source language must be auto, es, en, or pt.")
        if target_lang not in TARGET_LANGUAGES:
            raise ValueError("Target language must be es, en, or pt.")
        with self.lock:
            self.source_lang = source_lang
            self.target_lang = target_lang

    def to_dict(self, *, legacy_aliases: bool = True) -> dict:
        with self.lock:
            data = {
                "id": self.id,
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "status": self.status,
                "pending": self.pending,
                "error": self.error,
                "detected_lang": self.detected_lang,
                "generation": self.generation,
                "latency_ms": self.last_latency_ms,
                "queue_wait_ms": self.last_queue_wait_ms,
                "last_cue_at": self.last_cue_at,
                "title": self.title or f"Session {self.id}",
                "room": self.room,
                "agenda_lang": self.agenda_lang,
                "description": self.description,
                "tags": list(self.tags),
                "speakers": list(self.speakers),
                "image_url": self.image_url,
                "youtube_url": self.youtube_url,
                "track": self.track,
                "talk_id": self.talk_id,
                "watchers": self.watchers,
                "playback": {
                    "kind": self.playback_kind,
                    "has_media": self.playback_path is not None
                    and self.playback_path.is_file(),
                    "youtube_id": self.youtube_id,
                    "youtube_url": self.playback_url,
                    "is_live": self.youtube_is_live,
                    "stream_origin_at": self.stream_origin_at,
                    "delay_sec": self.playback_delay_sec()
                    if self.playback_kind == "youtube" and self.youtube_is_live
                    else None,
                    "chunk_seconds": self.live_chunk_seconds,
                    "ready_until": self.ready_until(),
                },
                "cues": [cue.to_dict() for cue in self.cues],
            }
            if legacy_aliases:
                status_es = {
                    "ready": "lista",
                    "preparing": "preparando",
                    "processing": "procesando",
                    "error": "error",
                }.get(data["status"], data["status"])
                data.update(
                    {
                        "idioma_origen": data["source_lang"],
                        "idioma_destino": data["target_lang"],
                        "estado": status_es,
                        "pendiente": data["pending"],
                        "idioma_detectado": data["detected_lang"],
                        "generacion": data["generation"],
                        "latencia_ms": data["latency_ms"],
                        "espera_cola_ms": data["queue_wait_ms"],
                        "ultimo_cue_at": data["last_cue_at"],
                        "titulo": data["title"],
                        "sala": data["room"],
                        "idioma_agenda": data["agenda_lang"],
                    }
                )
            return data


class SessionManager:
    """Own exactly K logical sessions for this process."""

    def __init__(self, sessions_per_gpu: int) -> None:
        if sessions_per_gpu < 1:
            raise ValueError("K must be greater than or equal to 1.")
        self.sessions_per_gpu = sessions_per_gpu
        self.sessions = {
            str(number): Session(id=str(number))
            for number in range(1, sessions_per_gpu + 1)
        }

    def get(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def apply_agenda(self, channels: list[dict]) -> None:
        for channel in channels:
            session = self.sessions.get(str(channel.get("id")))
            if session is None:
                continue
            session.title = channel.get("title") or channel.get("titulo")
            session.room = channel.get("room") or channel.get("sala")
            session.agenda_lang = channel.get("language") or channel.get("idioma")

    def apply_talks(self, talks: list[dict]) -> None:
        for index, talk in enumerate(talks[: self.sessions_per_gpu], start=1):
            session = self.sessions.get(str(index))
            if session is None:
                continue
            if session.status in {"processing", "preparing"}:
                continue
            session.apply_talk(talk)

    def list_dicts(self) -> list[dict]:
        return [session.to_dict() for session in self.sessions.values()]
