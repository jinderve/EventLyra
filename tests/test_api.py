"""API y página, con un motor falso. No se cargan pesos."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from eventlyra.config import Settings
from eventlyra.engine.audio import write_pcm_wav
from eventlyra.engine.runtime import SharedRuntime, instance_id
from eventlyra.server.app import MENSAJE_SIN_MODELOS, create_app, format_sse
from tests.test_runtime import FakeASR, FakeTranslator


def _settings(tmp_path: Path, k: int = 2) -> Settings:
    return Settings(
        sessions_per_gpu=k,
        work_dir=tmp_path,
        load_models=False,
        chunk_seconds=1.0,
    )


def _wav(path: Path, seconds: float) -> None:
    frames = int(seconds * 16000)
    write_pcm_wav(path, b"\x00\x00" * frames, 16000)


def _esperar(client: TestClient, session_id: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = client.get(f"/api/sessions/{session_id}").json()
        if last["pendiente"] == 0 and last["estado"] in {"lista", "error"} and last["cues"]:
            return last
        time.sleep(0.02)
    raise AssertionError(last)


def test_format_sse_es_un_evento():
    payload = format_sse("cue", {"original": "hola"})
    assert payload.startswith("event: cue\n")
    assert "hola" in payload
    assert payload.endswith("\n\n")


def test_sin_modelos_la_ui_abre_y_el_audio_responde_503(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert 'id="sesion"' in page.text
        assert 'id="linea-traduccion"' in page.text
        assert 'id="subtitulo-vivo"' in page.text
        assert 'class="subs"' in page.text
        health = client.get("/api/health").json()
        assert health["modelos_cargados"] is False
        assert health["sessions_per_gpu"] == 2
        assert health["mensaje"] == MENSAJE_SIN_MODELOS
        sesiones = client.get("/api/sessions").json()
        assert [item["id"] for item in sesiones["sesiones"]] == ["1", "2"]
        wav = tmp_path / "entrada.wav"
        _wav(wav, 0.5)
        with wav.open("rb") as handle:
            response = client.post(
                "/api/sessions/1/archivo",
                files={"archivo": ("entrada.wav", handle, "audio/wav")},
            )
        assert response.status_code == 503
        assert client.get("/api/sessions/3").status_code == 404


def test_dos_sesiones_comparten_el_motor_y_traducen(tmp_path):
    asr = FakeASR()
    translator = FakeTranslator()
    runtime = SharedRuntime(asr, translator)
    app = create_app(_settings(tmp_path), runtime=runtime)
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        assert health["pesos_compartidos"] is True
        assert health["asr_id"] == instance_id(asr)
        assert health["translator_id"] == instance_id(translator)
        assert health["modelo_traduccion"] == "google/translategemma-4b-it"
        assert health["cuantizacion_asr"] == "int8_float16"
        assert health["cuantizacion_traduccion"] == "bf16"

        patched = client.patch(
            "/api/sessions/1",
            json={"idioma_origen": "en", "idioma_destino": "es"},
        )
        assert patched.status_code == 200
        wav = tmp_path / "charla.wav"
        _wav(wav, 2.5)
        with wav.open("rb") as handle:
            uploaded = client.post(
                "/api/sessions/1/archivo",
                files={"archivo": ("charla.wav", handle, "audio/wav")},
            )
        assert uploaded.status_code == 200
        assert uploaded.json()["fragmentos"] == 3
        session = _esperar(client, "1")
        assert [cue["inicio"] for cue in session["cues"]] == [0.0, 1.0, 2.0]
        assert session["cues"][0]["original"] == "hello friends"
        assert session["cues"][0]["traduccion"] == "hello friends::en->es"
        assert session["idioma_destino"] == "es"

        client.patch(
            "/api/sessions/2",
            json={"idioma_origen": "es", "idioma_destino": "en"},
        )
        short = tmp_path / "otra.wav"
        _wav(short, 1.0)
        with short.open("rb") as handle:
            second = client.post(
                "/api/sessions/2/archivo",
                files={"archivo": ("otra.wav", handle, "audio/wav")},
            )
        assert second.status_code == 200
        other = _esperar(client, "2")
        assert other["cues"][0]["traduccion"] == "hello friends::es->en"
        again = client.get("/api/health").json()
        assert again["asr_id"] == health["asr_id"]
        assert again["translator_id"] == health["translator_id"]
        assert len(asr.calls) == 4


def test_reiniciar_limpia_cues_y_sube_la_generacion(tmp_path):
    runtime = SharedRuntime(FakeASR(), FakeTranslator())
    app = create_app(_settings(tmp_path), runtime=runtime)
    with TestClient(app) as client:
        wav = tmp_path / "charla.wav"
        _wav(wav, 1.0)
        with wav.open("rb") as handle:
            uploaded = client.post(
                "/api/sessions/1/archivo",
                files={"archivo": ("charla.wav", handle, "audio/wav")},
            )
        assert uploaded.status_code == 200
        before = uploaded.json()["generacion"]
        stopped = client.post("/api/sessions/1/reiniciar")
        assert stopped.status_code == 200
        data = stopped.json()
        assert data["generacion"] == before + 1
        assert data["cues"] == []
        assert data["pendiente"] == 0
        assert data["estado"] == "lista"


def test_archivo_vacio_y_extension_rechazada(tmp_path):
    runtime = SharedRuntime(FakeASR(), FakeTranslator())
    app = create_app(_settings(tmp_path), runtime=runtime)
    with TestClient(app) as client:
        empty = tmp_path / "vacio.wav"
        empty.write_bytes(b"")
        with empty.open("rb") as handle:
            response = client.post(
                "/api/sessions/1/archivo",
                files={"archivo": ("vacio.wav", handle, "audio/wav")},
            )
        assert response.status_code == 400
        bad = client.post(
            "/api/sessions/1/archivo",
            files={"archivo": ("notas.txt", b"hola", "text/plain")},
        )
        assert bad.status_code == 400


def test_la_interfaz_tiene_selector_de_sesion_e_idioma():
    html = Path("eventlyra/server/static/index.html").read_text(encoding="utf-8")
    js = Path("eventlyra/server/static/app.js").read_text(encoding="utf-8")
    assert 'id="sesion"' in html
    assert 'id="origen"' in html
    assert 'id="destino"' in html
    assert 'id="linea-original"' in html
    assert 'id="linea-traduccion"' in html
    assert 'id="subtitulo-vivo"' in html
    assert 'id="detener"' in html
    assert "elegirSesion" in js
    assert "/api/sessions" in js
    assert "/reiniciar" in js
    assert "pickSesionSync" in js
    assert "TAB_ID" in js
    assert "getUserMedia" in js


def test_el_setup_de_windows_deja_k_explicito_y_solo_el_4b():
    setup = Path("scripts/setup-windows.ps1").read_text(encoding="utf-8")
    run = Path("scripts/run-windows.ps1").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "google/translategemma-4b-it" in setup
    assert "translategemma-12b" not in setup
    assert "translategemma-27b" not in setup
    assert "hf auth login" in setup
    assert "E:\\EventLyra" in setup
    assert 'Join-Path $Raiz "venv"' in setup
    assert 'Join-Path $Raiz "hf-home"' in setup
    assert "Mandatory = $true" in run
    assert "SessionsPerGpu" in run
    assert "--sessions-per-gpu" in readme
    assert "huggingface.co/join" in readme
