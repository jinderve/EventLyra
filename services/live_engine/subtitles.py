"""SRT, VTT, and plain-text exports from session cues."""

from __future__ import annotations

from collections.abc import Sequence


def _clock(seconds: float, *, vtt: bool) -> str:
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    sep = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def _cue_lines(cue: dict) -> str:
    original = (cue.get("original") or "").strip()
    translation = (cue.get("translation") or cue.get("traduccion") or "").strip()
    if original and translation and original != translation:
        return f"{original}\n{translation}"
    return original or translation


def _start(cue: dict) -> float:
    value = cue.get("start")
    if value is None:
        value = cue.get("inicio") or 0
    return float(value)


def _end(cue: dict) -> float:
    value = cue.get("end")
    if value is None:
        value = cue.get("fin") or 0
    return float(value)


def cues_to_srt(cues: Sequence[dict]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        start = _clock(_start(cue), vtt=False)
        end = _clock(_end(cue), vtt=False)
        blocks.append(f"{index}\n{start} --> {end}\n{_cue_lines(cue)}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def cues_to_vtt(cues: Sequence[dict]) -> str:
    parts = ["WEBVTT", ""]
    for cue in cues:
        start = _clock(_start(cue), vtt=True)
        end = _clock(_end(cue), vtt=True)
        parts.append(f"{start} --> {end}\n{_cue_lines(cue)}")
        parts.append("")
    return "\n".join(parts).rstrip() + ("\n" if cues else "")


def cues_to_txt(cues: Sequence[dict]) -> str:
    lines = []
    for cue in cues:
        start = _clock(_start(cue), vtt=False)
        text = _cue_lines(cue).replace("\n", " | ")
        lines.append(f"[{start}] {text}")
    return "\n".join(lines) + ("\n" if lines else "")


def render_export(cues: Sequence[dict], fmt: str) -> tuple[str, str, str]:
    key = (fmt or "srt").lower()
    if key == "srt":
        return cues_to_srt(cues), "text/plain; charset=utf-8", "captions.srt"
    if key == "vtt":
        return cues_to_vtt(cues), "text/vtt; charset=utf-8", "captions.vtt"
    if key in {"txt", "text", "texto"}:
        return cues_to_txt(cues), "text/plain; charset=utf-8", "captions.txt"
    raise ValueError("fmt accepts srt, vtt, or txt.")
