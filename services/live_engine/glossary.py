"""Términos fijos de evento. Se aplican después de transcribir y traducir."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

GLOSSARY_PATH = (
    Path(__file__).resolve().parents[2] / "eventlyra" / "glossary" / "nerdearla.json"
)


def _patron(variante: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(variante)}(?!\w)", re.IGNORECASE)


@lru_cache(maxsize=1)
def load_terms(path: str | None = None) -> tuple[tuple[str, str], ...]:
    archivo = Path(path) if path else GLOSSARY_PATH
    data = json.loads(archivo.read_text(encoding="utf-8"))
    pares: list[tuple[str, str]] = []
    for item in data.get("terms", []):
        canonical = str(item["canonical"])
        variantes = [canonical, *item.get("variants", [])]
        vistos: set[str] = set()
        for variante in sorted(variantes, key=len, reverse=True):
            clave = variante.casefold()
            if not variante or clave in vistos:
                continue
            vistos.add(clave)
            pares.append((variante, canonical))
    return tuple(pares)


def apply_glossary(text: str, path: str | None = None) -> str:
    if not text:
        return text
    result = text
    for variant, canonical in load_terms(path):
        result = _patron(variant).sub(canonical, result)
    return result


aplicar_glosario = apply_glossary
