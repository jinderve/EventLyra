"""Borde de traducción. El único proveedor implementado es el local."""

from __future__ import annotations

from typing import Protocol

from eventlyra.config import PROVEEDOR_LOCAL, Settings


class Translator(Protocol):
    """Contrato que un proveedor futuro puede reemplazar."""

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Traduce `text` de `source_lang` a `target_lang`."""


def build_translator(provider: str, settings: Settings) -> Translator:
    """Devuelve el traductor del proceso.

    `vertex` queda reservado como nombre del reemplazo. No hay cliente de
    Vertex, Gemini ni GCP en este corte.
    """
    if provider == PROVEEDOR_LOCAL:
        from eventlyra.engine.local_gemma import LocalTranslateGemma

        return LocalTranslateGemma(settings)
    if provider == "vertex":
        raise NotImplementedError(
            "El proveedor de traducción 'vertex' no está implementado. "
            "El único proveedor disponible es 'local'."
        )
    raise ValueError(f"Proveedor de traducción desconocido: {provider}")
