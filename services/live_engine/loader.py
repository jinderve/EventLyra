"""Arranque del motor real. Importa torch y faster-whisper solo acá."""

from __future__ import annotations

import logging

from eventlyra.config import Settings
from services.transcription.providers.faster_whisper.provider import FasterWhisperTurbo
from services.live_engine.runtime import SharedRuntime, instance_id
from services.translation.base import build_translator

logger = logging.getLogger(__name__)


def build_local_runtime(settings: Settings) -> SharedRuntime:
    """Carga cada modelo una vez y devuelve el runtime compartido."""
    settings.validate()
    asr = FasterWhisperTurbo(settings)
    asr.load()
    translator = build_translator(settings.translator_provider, settings)
    translator.load()
    logger.info(
        "Se cargó una sola instancia de faster-whisper %s (%s, id %s) y de %s "
        "(%s, id %s). Este proceso atiende %s sesiones con esos mismos pesos.",
        settings.whisper_model,
        settings.whisper_compute_type,
        instance_id(asr),
        settings.translation_model_id,
        settings.translation_quantization,
        instance_id(translator),
        settings.sessions_per_gpu,
    )
    return SharedRuntime(asr, translator)
