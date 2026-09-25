"""El runtime comparte una instancia y la fábrica no llama a la nube."""

import threading
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


def _job(path: Path, source: str, target: str, results: list, done: threading.Event):
    from eventlyra.engine.runtime import ChunkJob

    return ChunkJob(
        wav_path=path,
        offset=0.0,
        source_lang=source,
        target_lang=target,
        is_current=lambda: True,
        resolve_language=lambda: None if source == "auto" else source,
        publish=_publicar(results, done),
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


def test_mismo_idioma_en_gemma_no_carga_pesos(tmp_path):
    settings = Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    translator = LocalTranslateGemma(settings)
    assert translator.translate("hola", "es", "es") == "hola"
    assert translator.loaded is False


def test_no_hay_cliente_de_gcp():
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("eventlyra").rglob("*.py")
    )
    assert "google.cloud" not in text
    assert "vertexai" not in text
    assert "generativelanguage" not in text


def test_whisper_transcribe_no_traduce():
    text = Path("eventlyra/engine/asr.py").read_text(encoding="utf-8")
    assert 'task="transcribe"' in text
    assert 'task="translate"' not in text
