"""Conversión a WAV mono 16 kHz y corte en fragmentos, sin modelos."""

from __future__ import annotations

import array
import os
import shutil
import subprocess
import wave
from pathlib import Path

from eventlyra.errors import AudioPrepError


def ffmpeg_executable() -> str:
    """Resuelve ffmpeg: env, PATH, o el paquete Gyan.FFmpeg de WinGet."""
    env = os.environ.get("EVENTLYRA_FFMPEG") or os.environ.get("FFMPEG")
    if env:
        path = Path(env)
        if path.is_dir():
            named = path / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if named.is_file():
                return str(named)
        elif path.is_file():
            return str(path)
    found = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if found:
        return found
    if os.name == "nt":
        packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
        if packages.is_dir():
            matches = sorted(packages.glob("Gyan.FFmpeg*/**/ffmpeg.exe"))
            if not matches:
                matches = sorted(packages.glob("**/ffmpeg.exe"))
            if matches:
                return str(matches[-1])
    raise AudioPrepError(
        "No se encontró ffmpeg en el PATH. En Windows lo instala scripts/setup-windows.ps1."
    )


def write_pcm_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    if sample_rate <= 0:
        raise AudioPrepError("La tasa de muestreo no es válida.")
    if len(pcm) % 2:
        raise AudioPrepError("El PCM tiene que ser de 16 bit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)


def is_target_wav(path: Path, sample_rate: int) -> bool:
    try:
        with wave.open(str(path), "rb") as handle:
            return (
                handle.getnchannels() == 1
                and handle.getsampwidth() == 2
                and handle.getframerate() == sample_rate
                and handle.getnframes() > 0
            )
    except (wave.Error, EOFError, FileNotFoundError):
        return False


def ffmpeg_to_wav(src: Path, dest: Path, sample_rate: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_executable(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(dest),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise AudioPrepError(
            "No se encontró ffmpeg. En Windows lo instala scripts/setup-windows.ps1."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        tail = detail[-500:] if detail else "sin detalle"
        raise AudioPrepError(f"ffmpeg no pudo convertir el archivo. {tail}") from exc


def prepare_wav(src: Path, dest: Path, sample_rate: int) -> None:
    """Deja un WAV mono 16-bit a `sample_rate` en `dest`."""
    if is_target_wav(src, sample_rate):
        if src.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        return
    ffmpeg_to_wav(src, dest, sample_rate)
    if not is_target_wav(dest, sample_rate):
        raise AudioPrepError("La conversión no produjo un WAV mono de 16 bit.")


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    if src_rate <= 0 or dst_rate <= 0:
        raise AudioPrepError("La tasa de muestreo no es válida.")
    if len(pcm) % 2:
        pcm = pcm[:-1]
    if src_rate == dst_rate or not pcm:
        return pcm
    source = array.array("h")
    source.frombytes(pcm)
    if len(source) == 1 or dst_rate == src_rate:
        return source.tobytes()
    dst_len = max(1, int(round(len(source) * dst_rate / src_rate)))
    destination = array.array("h", [0]) * dst_len
    if dst_len == 1:
        destination[0] = source[0]
        return destination.tobytes()
    scale = (len(source) - 1) / (dst_len - 1)
    for index in range(dst_len):
        position = index * scale
        left = int(position)
        frac = position - left
        right = min(left + 1, len(source) - 1)
        sample = source[left] + (source[right] - source[left]) * frac
        destination[index] = int(max(-32768, min(32767, round(sample))))
    return destination.tobytes()


def chunk_wav(
    src: Path,
    dest_dir: Path,
    chunk_seconds: float,
    sample_rate: int,
) -> list[tuple[float, Path, float]]:
    """Corta `src` en WAV consecutivos. Devuelve (offset, ruta, duración)."""
    if chunk_seconds <= 0:
        raise AudioPrepError("La ventana de audio tiene que ser mayor que 0.")
    if not is_target_wav(src, sample_rate):
        raise AudioPrepError("El WAV de trabajo no está en el formato esperado.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    pieces: list[tuple[float, Path, float]] = []
    with wave.open(str(src), "rb") as handle:
        rate = handle.getframerate()
        frames_per_chunk = max(1, int(chunk_seconds * rate))
        offset = 0.0
        index = 0
        while True:
            data = handle.readframes(frames_per_chunk)
            if not data:
                break
            duration = (len(data) // 2) / rate
            # La cola corta de un corte anterior se descarta; un audio breve se conserva.
            if duration < 0.3 and pieces:
                break
            path = dest_dir / f"fragmento-{index:04d}.wav"
            write_pcm_wav(path, data, rate)
            pieces.append((offset, path, duration))
            offset += duration
            index += 1
    return pieces
