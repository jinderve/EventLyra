"""Compatibility import; implementation moved to services.translation.providers.translategemma.provider."""

from services.translation.providers.translategemma.provider import (  # noqa: F401
    LocalTranslateGemma,
    _silenciar_aviso_matmul_8bit,
    is_degenerate_translation,
    traduccion_degenerada,
)
