"""Sesiones lógicas. No cargan modelos: solo estado y subtítulos."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from eventlyra.engine.types import Cue

ORIGENES = {"auto", "es", "en"}
DESTINOS = {"es", "en"}


@dataclass
class Session:
    id: str
    source_lang: str = "auto"
    target_lang: str = "es"
    status: str = "lista"
    pending: int = 0
    error: str | None = None
    detected_lang: str | None = None
    generation: int = 0
    next_index: int = 0
    cues: list[Cue] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    cond: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self.cond = threading.Condition(self.lock)

    def begin(self, status: str = "preparando") -> int:
        with self.lock:
            self.generation += 1
            self.cues.clear()
            self.pending = 0
            self.error = None
            self.detected_lang = None
            self.next_index = 0
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

    def set_languages(self, source_lang: str, target_lang: str) -> None:
        if source_lang not in ORIGENES:
            raise ValueError("El idioma original tiene que ser auto, es o en.")
        if target_lang not in DESTINOS:
            raise ValueError("El idioma de traducción tiene que ser es o en.")
        with self.lock:
            self.source_lang = source_lang
            self.target_lang = target_lang

    def to_dict(self) -> dict:
        with self.lock:
            return {
                "id": self.id,
                "idioma_origen": self.source_lang,
                "idioma_destino": self.target_lang,
                "estado": self.status,
                "pendiente": self.pending,
                "error": self.error,
                "idioma_detectado": self.detected_lang,
                "generacion": self.generation,
                "cues": [cue.to_dict() for cue in self.cues],
            }


class SessionManager:
    """Abre exactamente K sesiones fijas para este proceso."""

    def __init__(self, sessions_per_gpu: int) -> None:
        if sessions_per_gpu < 1:
            raise ValueError("K tiene que ser mayor o igual que 1.")
        self.sessions_per_gpu = sessions_per_gpu
        self.sessions = {
            str(number): Session(id=str(number))
            for number in range(1, sessions_per_gpu + 1)
        }

    def get(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def list_dicts(self) -> list[dict]:
        return [session.to_dict() for session in self.sessions.values()]
