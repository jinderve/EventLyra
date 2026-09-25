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
        "swapcard_url": "https://app.swapcard.com/event/nerdearla-2025/planning/UGxhbm5pbmdfMjc1OTU2NQ==",
        "nerdflix_url": "https://nerdearla.com/nerdflix/d567RerxDGk/",
    },
]


def extras_path(work_dir: Path) -> Path:
    return Path(work_dir) / "talks-extra.json"


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
    tags = payload.get("tags") or []
    speakers = payload.get("speakers") or []
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    if isinstance(speakers, str):
        speakers = [part.strip() for part in speakers.split(",") if part.strip()]
    talk = {
        "id": talk_id,
        "title": title,
        "room": (payload.get("room") or "").strip() or None,
        "track": (payload.get("track") or "").strip() or None,
        "language": (payload.get("language") or payload.get("source_lang") or "es"),
        "source_lang": payload.get("source_lang") or "auto",
        "target_lang": payload.get("target_lang") or "es",
        "speakers": list(speakers),
        "tags": list(tags),
        "description": (payload.get("description") or "").strip() or None,
        "image_url": (payload.get("image_url") or "").strip() or None,
        "youtube_url": (payload.get("youtube_url") or "").strip() or None,
    }
    extras.append(talk)
    save_extras(work_dir, extras)
    return talk


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
            }
        )
    return decorated
