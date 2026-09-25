#!/usr/bin/env python3
"""Convierte un audio o video local a WAV mono de 16 kHz dentro de samples/.

No baja modelos ni abre la red. El WAV queda ignorado por git.

Ejemplo:
  python scripts/preparar-muestra.py D:\\charla.mp4 --nombre sesion-1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventlyra.engine.audio import prepare_wav  # noqa: E402
from eventlyra.errors import AudioPrepError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepara un WAV de prueba en samples/.")
    parser.add_argument("origen", type=Path, help="Archivo de audio o video local.")
    parser.add_argument(
        "--nombre",
        default="muestra",
        help="Nombre del WAV, sin extensión. Queda en samples/<nombre>.wav.",
    )
    parser.add_argument("--sample-rate", type=int, default=16000)
    args = parser.parse_args(argv)
    if not args.origen.is_file():
        print(f"No se encontró {args.origen}", file=sys.stderr)
        return 1
    if any(sep in args.nombre for sep in ("/", "\\", "..")):
        print("El nombre tiene que ser un solo tramo, sin carpetas.", file=sys.stderr)
        return 1
    dest = ROOT / "samples" / f"{args.nombre}.wav"
    try:
        prepare_wav(args.origen, dest, args.sample_rate)
    except AudioPrepError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Se escribió {dest}")
    print("Cargalo en la interfaz con el selector de archivo. Git no lo versiona.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
