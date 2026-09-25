"""Event talk catalog. K GPU channels bind the first K talks; extras stay in Events."""

from __future__ import annotations

import json
import re
from pathlib import Path

DEFAULT_TALKS: list[dict] = [
    {
        "id": "salatino-feedback",
        "title": "Cómo recibir feedback sin desmotivarte ni querer renunciar (incluso cuando está mal dado)",
        "room": "Stream B",
        "track": "SOFTSKILLS",
        "language": "es",
        "source_lang": "es",
        "target_lang": "en",
        "speakers": ["Verónica Salatino"],
        "tags": ["softskills", "liderazgo", "comunicación", "coaching"],
        "description": (
            "Recibir feedback puede ser uno de los momentos más incómodos de la vida laboral. "
            "Esta charla muestra cómo escuchar críticas sin caer en el ego y cómo usar incluso "
            "el peor comentario como palanca de crecimiento."
        ),
        "image_url": "https://img.youtube.com/vi/37oDPQGB8Ww/maxresdefault.jpg",
        "youtube_url": "https://www.youtube.com/watch?v=37oDPQGB8Ww",
        "audio_kind": "url",
        "published": True,
        "swapcard_url": "https://app.swapcard.com/event/nerdearla-2025/planning/UGxhbm5pbmdfMjc3NjA0Mg==",
        "nerdflix_url": "https://nerdearla.com/nerdflix/37oDPQGB8Ww/",
    },
    {
        "id": "tanenbaum-interview",
        "title": "Interview with Andrew S. Tanenbaum",
        "room": "Stream A",
        "track": "DEVELOPMENT",
        "language": "en",
        "source_lang": "en",
        "target_lang": "es",
        "speakers": ["Andrew S. Tanenbaum", "Nicolás Wolovick"],
        "tags": ["development", "systems", "open-source"],
        "description": (
            "Andrew S. Tanenbaum (AST) at Nerdearla Argentina 2025, in conversation with "
            "Nicolás Wolovick. Operating systems, MINIX, and computer security."
        ),
        "image_url": "https://img.youtube.com/vi/d567RerxDGk/maxresdefault.jpg",
        "youtube_url": "https://www.youtube.com/watch?v=d567RerxDGk",
        "audio_kind": "url",
        "published": True,
        "swapcard_url": "https://app.swapcard.com/event/nerdearla-2025/planning/UGxhbm5pbmdfMjc1OTU2NQ==",
        "nerdflix_url": "https://nerdearla.com/nerdflix/d567RerxDGk/",
    },
]

EDITABLE_FIELDS = {
    "title",
    "room",
    "track",
    "description",
    "tags",
    "speakers",
    "image_url",
    "youtube_url",
    "source_lang",
    "target_lang",
    "language",
    "audio_kind",
    "published",
}


def extras_path(work_dir: Path) -> Path:
    return Path(work_dir) / "talks-extra.json"


def overrides_path(work_dir: Path) -> Path:
    return Path(work_dir) / "talks-overrides.json"


def _as_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def _apply_fields(talk: dict, payload: dict) -> dict:
    for key in EDITABLE_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        if key in {"tags", "speakers"}:
            talk[key] = _as_list(value)
        elif key == "published":
            talk[key] = bool(value)
        elif key in {"title", "room", "track", "description", "image_url", "youtube_url"}:
            text = "" if value is None else str(value).strip()
            talk[key] = text or None
            if key == "title" and not talk[key]:
                raise ValueError("A talk title is required.")
        else:
            talk[key] = value
    if talk.get("youtube_url") and not talk.get("audio_kind"):
        talk["audio_kind"] = "url"
    return talk


def load_overrides(work_dir: Path) -> dict[str, dict]:
    path = overrides_path(work_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(key): value
        for key, value in data.items()
        if isinstance(value, dict)
    }


def save_overrides(work_dir: Path, overrides: dict[str, dict]) -> None:
    path = overrides_path(work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")


def load_extras(work_dir: Path) -> list[dict]:
    path = extras_path(work_dir)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("title")]


def save_extras(work_dir: Path, extras: list[dict]) -> None:
    path = extras_path(work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(extras, ensure_ascii=False, indent=2), encoding="utf-8")


def load_talks(work_dir: Path | None = None) -> list[dict]:
    talks = [dict(item) for item in DEFAULT_TALKS]
    if work_dir is not None:
        overrides = load_overrides(work_dir)
        for talk in talks:
            extra = overrides.get(str(talk.get("id")))
            if extra:
                talk.update(extra)
        talks.extend(load_extras(work_dir))
    return talks


def slugify(title: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return text[:48] or "talk"


def add_talk(work_dir: Path, payload: dict) -> dict:
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("A talk title is required.")
    extras = load_extras(work_dir)
    talk_id = str(payload.get("id") or "").strip() or slugify(title)
    if any(item.get("id") == talk_id for item in DEFAULT_TALKS + extras):
        talk_id = f"{talk_id}-{len(extras) + 1}"
    youtube_url = (payload.get("youtube_url") or "").strip() or None
    talk = {
        "id": talk_id,
        "title": title,
        "room": (payload.get("room") or "").strip() or None,
        "track": (payload.get("track") or "").strip() or None,
        "language": (payload.get("language") or payload.get("source_lang") or "es"),
        "source_lang": payload.get("source_lang") or "auto",
        "target_lang": payload.get("target_lang") or "es",
        "speakers": _as_list(payload.get("speakers")),
        "tags": _as_list(payload.get("tags")),
        "description": (payload.get("description") or "").strip() or None,
        "image_url": (payload.get("image_url") or "").strip() or None,
        "youtube_url": youtube_url,
        "audio_kind": payload.get("audio_kind") or ("url" if youtube_url else None),
        "published": bool(payload.get("published", False)),
    }
    extras.append(talk)
    save_extras(work_dir, extras)
    return talk


def update_talk(work_dir: Path, talk_id: str, payload: dict) -> dict:
    extras = load_extras(work_dir)
    for item in extras:
        if item.get("id") == talk_id:
            _apply_fields(item, payload)
            save_extras(work_dir, extras)
            return item
    if any(item.get("id") == talk_id for item in DEFAULT_TALKS):
        overrides = load_overrides(work_dir)
        current = dict(overrides.get(talk_id) or {})
        _apply_fields(current, payload)
        current["id"] = talk_id
        overrides[talk_id] = current
        save_overrides(work_dir, overrides)
        base = next(item for item in DEFAULT_TALKS if item["id"] == talk_id)
        return {**base, **current}
    raise ValueError("Talk not found.")


def decorate_talks(talks: list[dict], k: int, sessions: list[dict]) -> list[dict]:
    by_id = {item["id"]: item for item in sessions}
    decorated = []
    for index, talk in enumerate(talks):
        channel_id = str(index + 1) if index < k else None
        session = by_id.get(channel_id) if channel_id else None
        status = session.get("status") if session else "catalog"
        decorated.append(
            {
                **talk,
                "channel_id": channel_id,
                "status": status,
                "live": status == "processing",
                "published": bool(talk.get("published")),
                "audio_kind": talk.get("audio_kind")
                or ("url" if talk.get("youtube_url") else None),
            }
        )
    return decorated
