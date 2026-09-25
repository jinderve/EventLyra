"""Parámetros del proceso. K no tiene valor oculto: hay que pasarlo."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

# Único modelo de traducción de este corte. Los 12B y 27B no se bajan ni se cargan.
TRANSLATEGEMMA_4B = "google/translategemma-4b-it"
# Alias de faster-whisper. El repo real es WHISPER_TURBO_REPO.
WHISPER_TURBO = "turbo"
WHISPER_TURBO_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
# INT8 en GPU según faster-whisper: pesos INT8 y cómputo float16.
WHISPER_COMPUTE_INT8_GPU = "int8_float16"
TRANSLATION_QUANT_8BIT = "8bit"
TRANSLATION_DTYPE_BF16 = "bf16"
PROVEEDOR_LOCAL = "local"
MODELOS_GRANDES_EXCLUIDOS = ("translategemma-12b", "translategemma-27b")


@dataclass(frozen=True)
class Settings:
    """Configuración de un proceso. Una GPU atiende K sesiones."""

    sessions_per_gpu: int
    host: str = "127.0.0.1"
    port: int = 8000
    work_dir: Path = Path(".work")
    chunk_seconds: float = 8.0
    sample_rate: int = 16000
    load_models: bool = True
    whisper_model: str = WHISPER_TURBO
    whisper_device: str = "cuda"
    whisper_compute_type: str = WHISPER_COMPUTE_INT8_GPU
    translation_model_id: str = TRANSLATEGEMMA_4B
    translation_quantization: str = TRANSLATION_DTYPE_BF16
    translator_provider: str = PROVEEDOR_LOCAL

    def validate(self) -> None:
        if self.sessions_per_gpu < 1:
            raise ValueError(
                "K (--sessions-per-gpu) tiene que ser un entero mayor o igual que 1."
            )
        if self.chunk_seconds <= 0:
            raise ValueError("--chunk-seconds tiene que ser mayor que 0.")
        if self.sample_rate < 8000:
            raise ValueError("La tasa de muestreo de trabajo tiene que ser al menos 8000 Hz.")
        modelo = self.translation_model_id.lower()
        if any(excluido in modelo for excluido in MODELOS_GRANDES_EXCLUIDOS):
            raise ValueError(
                "Este corte solo usa google/translategemma-4b-it. "
                "No se carga TranslateGemma 12B ni 27B."
            )
        if self.translation_quantization != TRANSLATION_DTYPE_BF16:
            raise ValueError("La traducción local de este corte carga el 4B en bf16, no en 8-bit.")
        if self.translator_provider != PROVEEDOR_LOCAL:
            raise ValueError("El único proveedor implementado es 'local'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eventlyra",
        description=(
            "Servidor local de subtítulos. K es la cantidad de sesiones que "
            "este proceso atiende con una sola copia de los modelos."
        ),
    )
    parser.add_argument(
        "--sessions-per-gpu",
        type=int,
        required=True,
        metavar="K",
        help="Cantidad de sesiones simultáneas de este proceso y esta GPU.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(".work"),
        help="Directorio temporal de audio. En Windows el script lo pone en E:\\.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=float,
        default=8.0,
        help="Duración de cada fragmento de audio que entra a la cola de la GPU.",
    )
    parser.add_argument(
        "--sin-modelos",
        action="store_true",
        help="Abre la interfaz sin cargar pesos. No produce subtítulos reales.",
    )
    return parser


def settings_from_argv(argv: list[str] | None = None) -> Settings:
    args = build_parser().parse_args(argv)
    settings = Settings(
        sessions_per_gpu=args.sessions_per_gpu,
        host=args.host,
        port=args.port,
        work_dir=args.work_dir,
        chunk_seconds=args.chunk_seconds,
        load_models=not args.sin_modelos,
    )
    settings.validate()
    return settings
