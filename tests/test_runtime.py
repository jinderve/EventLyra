"""El runtime comparte una instancia y la fábrica no llama a la nube."""

import threading
import time
from pathlib import Path

import pytest

from eventlyra.config import Settings
from eventlyra.engine.local_gemma import LocalTranslateGemma
from eventlyra.engine.runtime import SharedRuntime, instance_id
from eventlyra.engine.translator import build_translator
from eventlyra.engine.types import Transcript, TranscriptSegment


class FakeASR:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def transcribe(self, path, language: str | None) -> Transcript:
        self.calls.append((str(path), language))
        return Transcript(
            language=language or "en",
            segments=[TranscriptSegment(0.0, 0.4, "hello friends")],
        )


class FakeTranslator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        self.calls.append((text, source_lang, target_lang))
        return f"{text}::{source_lang}->{target_lang}"


def _publicar(results: list, done: threading.Event):
    def publish(cues, detected, error):
        results.append((cues, detected, error))
        done.set()

    return publish


def _job(path: Path, source: str, target: str, results: list, done: threading.Event, session_id: str = "1"):
    from eventlyra.engine.runtime import ChunkJob

    return ChunkJob(
        wav_path=path,
        offset=0.0,
        source_lang=source,
        target_lang=target,
        is_current=lambda: True,
        resolve_language=lambda: None if source == "auto" else source,
        publish=_publicar(results, done),
        session_id=session_id,
    )


def test_dos_trabajos_usan_el_mismo_objeto(tmp_path):
    asr = FakeASR()
    translator = FakeTranslator()
    runtime = SharedRuntime(asr, translator)
    runtime.start()
    try:
        first: list = []
        second: list = []
        done_a = threading.Event()
        done_b = threading.Event()
        runtime.submit(_job(tmp_path / "a.wav", "en", "es", first, done_a))
        runtime.submit(_job(tmp_path / "b.wav", "es", "en", second, done_b))
        assert done_a.wait(2)
        assert done_b.wait(2)
    finally:
        runtime.stop()
    assert len(asr.calls) == 2
    assert first[0][0][0].translation == "hello friends::en->es"
    assert second[0][0][0].translation == "hello friends::es->en"
    assert instance_id(runtime.asr) == instance_id(asr)
    assert instance_id(runtime.translator) == instance_id(translator)


def test_la_gpu_se_reparte_entre_sesiones(tmp_path):
    asr = FakeASR()
    translator = FakeTranslator()
    runtime = SharedRuntime(asr, translator)
    dones = [threading.Event() for _ in range(3)]
    results: list[list] = [[], [], []]
    runtime.submit(_job(tmp_path / "a.wav", "en", "es", results[0], dones[0], session_id="1"))
    runtime.submit(_job(tmp_path / "b.wav", "en", "es", results[1], dones[1], session_id="1"))
    runtime.submit(_job(tmp_path / "c.wav", "es", "en", results[2], dones[2], session_id="2"))
    runtime.start()
    try:
        assert all(item.wait(2) for item in dones)
    finally:
        runtime.stop()
    nombres = [Path(call[0]).name for call in asr.calls]
    assert nombres == ["a.wav", "c.wav", "b.wav"]


def test_dos_wav_en_el_mismo_directorio_no_se_pisan(tmp_path):
    from eventlyra.engine.audio import write_pcm_wav
    from eventlyra.engine.jobs import enqueue_wav
    from eventlyra.engine.sessions import Session

    class SlowASR(FakeASR):
        def transcribe(self, path, language: str | None) -> Transcript:
            assert Path(path).is_file(), path
            time.sleep(0.08)
            return super().transcribe(path, language)

    settings = Settings(
        sessions_per_gpu=1,
        work_dir=tmp_path,
        load_models=False,
        chunk_seconds=1.0,
    )
    session = Session(id="1")
    generation = session.begin()
    runtime = SharedRuntime(SlowASR(), FakeTranslator())
    first = tmp_path / "live-0000.wav"
    second = tmp_path / "live-0001.wav"
    write_pcm_wav(first, b"\x00\x00" * 16000, 16000)
    write_pcm_wav(second, b"\x00\x00" * 16000, 16000)
    runtime.start()
    try:
        assert enqueue_wav(session, first, settings, runtime, generation, 0.0) == 1
        assert enqueue_wav(session, second, settings, runtime, generation, 1.0) == 1
        deadline = time.time() + 3
        while time.time() < deadline:
            with session.lock:
                if session.pending == 0 and session.status in {"ready", "error"}:
                    break
            time.sleep(0.02)
        with session.lock:
            assert session.error is None, session.error
            assert session.pending == 0
            assert len(session.cues) == 2
    finally:
        runtime.stop()


def test_latencia_es_inferencia_no_espera_de_cola(tmp_path):
    class SlowASR(FakeASR):
        def transcribe(self, path, language: str | None) -> Transcript:
            time.sleep(0.12)
            return super().transcribe(path, language)

    asr = SlowASR()
    translator = FakeTranslator()
    runtime = SharedRuntime(asr, translator)
    dones = [threading.Event() for _ in range(2)]
    results: list[list] = [[], []]
    runtime.submit(_job(tmp_path / "a.wav", "en", "es", results[0], dones[0], session_id="1"))
    runtime.submit(_job(tmp_path / "b.wav", "en", "es", results[1], dones[1], session_id="1"))
    runtime.start()
    try:
        assert all(item.wait(3) for item in dones)
    finally:
        runtime.stop()
    first = results[0][0][0][0]
    second = results[1][0][0][0]
    assert first.latency_ms is not None
    assert second.latency_ms is not None
    assert abs(first.latency_ms - second.latency_ms) < 80
    assert (second.queue_wait_ms or 0) >= (first.queue_wait_ms or 0)
    assert (second.queue_wait_ms or 0) >= 80


def test_el_mismo_idioma_no_llama_al_traductor(tmp_path):
    asr = FakeASR()
    translator = FakeTranslator()
    runtime = SharedRuntime(asr, translator)
    results: list = []
    done = threading.Event()
    runtime.start()
    try:
        runtime.submit(_job(tmp_path / "a.wav", "es", "es", results, done))
        assert done.wait(2)
    finally:
        runtime.stop()
    assert translator.calls == []
    assert results[0][0][0].translation == "hello friends"


def test_vertex_no_esta_implementado(tmp_path):
    settings = Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    with pytest.raises(NotImplementedError):
        build_translator("vertex", settings)


def test_proveedor_desconocido(tmp_path):
    settings = Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    with pytest.raises(ValueError):
        build_translator("gemini", settings)


def test_aviso_matmul_8bit_se_silencia():
    import logging

    from eventlyra.engine.local_gemma import _silenciar_aviso_matmul_8bit

    _silenciar_aviso_matmul_8bit()
    assert logging.getLogger("bitsandbytes.autograd._functions").level == logging.ERROR


def test_mismo_idioma_en_gemma_no_carga_pesos(tmp_path):
    settings = Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    translator = LocalTranslateGemma(settings)
    assert translator.translate("hola", "es", "es") == "hola"
    assert translator.loaded is False


def test_no_hay_cliente_de_gcp():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for folder in (Path("eventlyra"), Path("services"), Path("apps"))
        for path in folder.rglob("*.py")
        if path.is_file()
    )
    assert "google.cloud" not in text
    assert "vertexai" not in text
    assert "generativelanguage" not in text


def test_whisper_transcribe_no_traduce():
    text = Path("services/transcription/providers/faster_whisper/provider.py").read_text(
        encoding="utf-8"
    )
    assert 'task="transcribe"' in text
    assert 'task="translate"' not in text
    assert "condition_on_previous_text=False" in text


def test_idioma_auto_no_se_queda_con_ingles_flojo():
    from eventlyra.engine.asr import idioma_de_info, parece_espanol

    frase = "vamos a verlo ahora el feedback principal porque está mal"
    assert parece_espanol(frase)
    assert idioma_de_info(None, "en", 0.99, frase) == "es"
    assert idioma_de_info("en", "es", 0.99, frase) == "en"
    from eventlyra.engine.asr import parece_portugues

    pt = "você não está a ver a tradução"
    assert parece_portugues(pt)
    assert idioma_de_info(None, "en", 0.99, pt) == "pt"
    assert idioma_de_info("pt", "en", 0.99, "hello") == "pt"


def test_traduccion_basura_se_marca():
    from eventlyra.engine.local_gemma import traduccion_degenerada

    assert traduccion_degenerada("Universidad de Córdoba. Soy docente.") is False
    assert traduccion_degenerada("olandkiewicz inequoi செ hardnessadona ட్డ তাল") is True
