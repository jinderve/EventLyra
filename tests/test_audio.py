"""Audio de trabajo, sin modelos."""

import shutil
import wave
from pathlib import Path

import pytest

from eventlyra.engine.audio import (
    chunk_wav,
    is_target_wav,
    prepare_wav,
    resample_pcm16,
    write_pcm_wav,
)
from eventlyra.errors import AudioPrepError


def _silencio(path: Path, seconds: float, rate: int = 16000, channels: int = 1) -> None:
    frames = int(seconds * rate)
    pcm = b"\x00\x00" * frames * channels
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm)


def test_resample_mantiene_la_tasa():
    pcm = b"\x00\x10" * 160
    assert resample_pcm16(pcm, 16000, 16000) == pcm


def test_resample_baja_la_cantidad_de_muestras():
    pcm = b"\x00\x10" * 480
    out = resample_pcm16(pcm, 48000, 16000)
    assert len(out) == 320  # 160 muestras * 2 bytes


def test_chunk_wav_respeta_la_ventana(tmp_path):
    src = tmp_path / "largo.wav"
    _silencio(src, seconds=2.5)
    pieces = chunk_wav(src, tmp_path / "out", chunk_seconds=1.0, sample_rate=16000)
    assert [round(item[0], 2) for item in pieces] == [0.0, 1.0, 2.0]
    assert [round(item[2], 2) for item in pieces] == [1.0, 1.0, 0.5]
    assert all(is_target_wav(item[1], 16000) for item in pieces)


def test_prepare_wav_copia_si_ya_esta_en_formato(tmp_path):
    src = tmp_path / "ok.wav"
    dest = tmp_path / "copia.wav"
    _silencio(src, seconds=0.4)
    prepare_wav(src, dest, 16000)
    assert is_target_wav(dest, 16000)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no está en el PATH")
def test_prepare_wav_convierte_stereo(tmp_path):
    src = tmp_path / "stereo.wav"
    dest = tmp_path / "mono.wav"
    _silencio(src, seconds=0.4, channels=2)
    prepare_wav(src, dest, 16000)
    with wave.open(str(dest)) as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == 16000


def test_chunk_rechaza_un_wav_que_no_es_de_trabajo(tmp_path):
    src = tmp_path / "stereo.wav"
    _silencio(src, seconds=0.4, channels=2)
    with pytest.raises(AudioPrepError):
        chunk_wav(src, tmp_path / "out", 1.0, 16000)


def test_write_pcm_wav_redondo(tmp_path):
    path = tmp_path / "a.wav"
    write_pcm_wav(path, b"\x01\x00" * 16, 16000)
    assert is_target_wav(path, 16000)
