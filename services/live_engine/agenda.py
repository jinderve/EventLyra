"""Cached public Nerdearla schedule. The engine never depends on it."""

from __future__ import annotations

import json
from pathlib import Path

CACHE_PATH = (
    Path(__file__).resolve().parents[2] / "eventlyra" / "agenda" / "cache.json"
)

_LANG = {
    "english": "en",
    "en": "en",
    "spanish": "es",
    "es": "es",
    "portuguese": "pt",
    "portugués": "pt",
    "pt": "pt",
}


def language_code(raw: str | None) -> str:
    if not raw:
        return "es"
    return _LANG.get(raw.strip().lower(), "es")


def load_cache(path: Path | None = None) -> dict:
    archivo = path or CACHE_PATH
    if not archivo.is_file():
        return {"edition": {}, "sessions": []}
    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"edition": {}, "sessions": []}
    if not isinstance(data, dict):
        return {"edition": {}, "sessions": []}
    data.setdefault("edition", {})
    data.setdefault("sessions", [])
    return data


def channels_for_k(cache: dict, k: int) -> list[dict]:
    talks = [item for item in cache.get("sessions", []) if item.get("title")]
    en = [item for item in talks if language_code(item.get("language")) == "en"]
    es = [item for item in talks if language_code(item.get("language")) == "es"]
    ordered: list[dict] = []
    seen: set[str] = set()

    def take(item: dict | None) -> None:
        if item is None:
            return
        clave = str(item.get("id") or item.get("slug") or item.get("title"))
        if clave in seen:
            return
        seen.add(clave)
        ordered.append(item)

    for ingles, espanol in zip(en, es):
        take(ingles)
        take(espanol)
    if len(en) > len(es):
        for item in en[len(es) :]:
            take(item)
    elif len(es) > len(en):
        for item in es[len(en) :]:
            take(item)
    for item in talks:
        take(item)
    channels = []
    for index in range(1, max(1, k) + 1):
        talk = ordered[index - 1] if index - 1 < len(ordered) else None
        if talk is None:
            channels.append(
                {
                    "id": str(index),
                    "title": f"Session {index}",
                    "room": None,
                    "language": None,
                    "slug": None,
                }
            )
            continue
        channels.append(
            {
                "id": str(index),
                "title": talk.get("title") or f"Session {index}",
                "room": talk.get("room") or talk.get("location_name"),
                "language": language_code(talk.get("language")),
                "slug": talk.get("slug"),
            }
        )
    return channels


def canales_para_k(cache: dict, k: int) -> list[dict]:
    """Deprecated Spanish response shape for the legacy client."""
    return [
        {
            **channel,
            "titulo": channel["title"],
            "sala": channel["room"],
            "idioma": channel["language"],
        }
        for channel in channels_for_k(cache, k)
    ]
