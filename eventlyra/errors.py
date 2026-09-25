"""Errores que la API puede mostrar en la interfaz."""


class EventLyraError(Exception):
    """Error de dominio con un mensaje listo para mostrar."""


class ModelosNoCargados(EventLyraError):
    """El proceso arrancó sin los pesos locales."""


class AudioPrepError(EventLyraError):
    """El archivo o el PCM no pudo convertirse a WAV de trabajo."""
