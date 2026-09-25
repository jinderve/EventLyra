"""API local y la página de subtítulos."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from eventlyra import __version__
from eventlyra.config import Settings
from eventlyra.engine.audio import prepare_wav, resample_pcm16, write_pcm_wav
from eventlyra.engine.jobs import enqueue_wav
from eventlyra.engine.loader import build_local_runtime
from eventlyra.engine.runtime import SharedRuntime, instance_id
from eventlyra.engine.sessions import DESTINOS, ORIGENES, Session, SessionManager
from eventlyra.errors import AudioPrepError

STATIC_DIR = Path(__file__).resolve().parent / "static"
ALLOWED_SUFFIXES = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
    ".webm",
    ".mp4",
    ".mkv",
    ".mov",
}
MENSAJE_SIN_MODELOS = (
    "Los modelos no están cargados en este proceso. "
    "En la PC con la GPU, corré scripts/setup-windows.ps1 y arrancá sin --sin-modelos."
)


def format_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def create_app(settings: Settings, runtime: SharedRuntime | None = None) -> FastAPI:
    settings.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings.work_dir.mkdir(parents=True, exist_ok=True)
        if app.state.runtime is None and app.state.settings.load_models:
            app.state.runtime = await asyncio.to_thread(
                build_local_runtime, app.state.settings
            )
        if app.state.runtime is not None:
            app.state.runtime.start()
        yield
        if app.state.runtime is not None:
            app.state.runtime.stop()

    app = FastAPI(title="EventLyra", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = SessionManager(settings.sessions_per_gpu)
    app.state.runtime = runtime

    def require_session(session_id: str) -> Session:
        session = app.state.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"La sesión {session_id} no existe en este proceso. "
                    f"K = {settings.sessions_per_gpu}. "
                    "Para más sesiones, subí K o levantá el mismo API en otra GPU."
                ),
            )
        return session

    def require_runtime() -> SharedRuntime:
        current = app.state.runtime
        if current is None:
            raise HTTPException(status_code=503, detail=MENSAJE_SIN_MODELOS)
        return current

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict:
        current = app.state.runtime
        loaded = current is not None
        return {
            "ok": True,
            "version": __version__,
            "modelos_cargados": loaded,
            "pesos_compartidos": loaded,
            "sessions_per_gpu": settings.sessions_per_gpu,
            "proveedor_traduccion": settings.translator_provider,
            "modelo_asr": settings.whisper_model,
            "cuantizacion_asr": settings.whisper_compute_type,
            "modelo_traduccion": settings.translation_model_id,
            "cuantizacion_traduccion": settings.translation_quantization,
            "chunk_seconds": settings.chunk_seconds,
            "asr_id": instance_id(current.asr) if loaded else None,
            "translator_id": instance_id(current.translator) if loaded else None,
            "mensaje": None if loaded else MENSAJE_SIN_MODELOS,
        }

    @app.get("/api/sessions")
    def listar_sesiones() -> dict:
        return {
            "sessions_per_gpu": settings.sessions_per_gpu,
            "sesiones": app.state.sessions.list_dicts(),
        }

    @app.get("/api/sessions/{session_id}")
    def obtener_sesion(session_id: str) -> dict:
        return require_session(session_id).to_dict()

    @app.patch("/api/sessions/{session_id}")
    async def actualizar_idioma(session_id: str, request: Request) -> dict:
        session = require_session(session_id)
        body = await request.json()
        source = body.get("idioma_origen", session.source_lang)
        target = body.get("idioma_destino", session.target_lang)
        if source not in ORIGENES or target not in DESTINOS:
            raise HTTPException(
                status_code=400,
                detail="idioma_origen admite auto, es o en. idioma_destino admite es o en.",
            )
        session.set_languages(source, target)
        return session.to_dict()

    @app.post("/api/sessions/{session_id}/reiniciar")
    def reiniciar(session_id: str) -> dict:
        session = require_session(session_id)
        session.begin(status="lista")
        return session.to_dict()

    @app.post("/api/sessions/{session_id}/archivo")
    async def subir_archivo(
        session_id: str,
        archivo: UploadFile = File(...),
    ) -> dict:
        session = require_session(session_id)
        runtime = require_runtime()
        filename = archivo.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail="El archivo tiene que ser audio o video (wav, mp3, m4a, mp4, webm, mkv).",
            )
        generation = session.begin()
        directory = _session_dir(settings, session_id, generation)
        upload_path = directory / f"entrada{suffix}"
        try:
            with upload_path.open("wb") as handle:
                while True:
                    chunk = await archivo.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            if upload_path.stat().st_size == 0:
                raise AudioPrepError("El archivo está vacío.")
            wav_path = directory / "fuente.wav"

            def prepare() -> int:
                prepare_wav(upload_path, wav_path, settings.sample_rate)
                upload_path.unlink(missing_ok=True)
                return enqueue_wav(
                    session,
                    wav_path,
                    settings,
                    runtime,
                    generation,
                    0.0,
                )

            count = await asyncio.to_thread(prepare)
        except AudioPrepError as exc:
            session.fail_if_current(generation, str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            session.fail_if_current(generation, "No se pudo preparar el audio.")
            raise HTTPException(status_code=500, detail="No se pudo preparar el audio.") from exc
        return {"fragmentos": count, "generacion": generation}

    @app.post("/api/sessions/{session_id}/pcm")
    async def subir_pcm(
        session_id: str,
        request: Request,
        sample_rate: int,
        inicio: float = 0.0,
    ) -> dict:
        session = require_session(session_id)
        runtime = require_runtime()
        if sample_rate < 8000 or sample_rate > 96000:
            raise HTTPException(status_code=400, detail="sample_rate fuera de rango.")
        if inicio < 0:
            raise HTTPException(status_code=400, detail="inicio no puede ser negativo.")
        raw = await request.body()
        if len(raw) < 2:
            raise HTTPException(status_code=400, detail="El audio está vacío.")
        generation = session.generation
        directory = _session_dir(settings, session_id, generation)
        wav_path = directory / f"pcm-{inicio:.3f}.wav".replace(":", "-")

        def prepare() -> int:
            pcm = resample_pcm16(raw, sample_rate, settings.sample_rate)
            min_bytes = int(settings.sample_rate * 0.3) * 2
            if len(pcm) < min_bytes:
                return 0
            write_pcm_wav(wav_path, pcm, settings.sample_rate)
            return enqueue_wav(
                session,
                wav_path,
                settings,
                runtime,
                generation,
                inicio,
            )

        try:
            count = await asyncio.to_thread(prepare)
        except AudioPrepError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"fragmentos": count, "generacion": generation}

    @app.get("/api/sessions/{session_id}/eventos")
    def eventos(session_id: str) -> StreamingResponse:
        session = require_session(session_id)

        async def stream():
            sent = 0
            last_marker = None
            while True:
                with session.lock:
                    generation = session.generation
                    cues = [cue.to_dict() for cue in session.cues]
                    status = {
                        "estado": session.status,
                        "pendiente": session.pending,
                        "error": session.error,
                        "generacion": generation,
                        "idioma_detectado": session.detected_lang,
                    }
                if sent > len(cues):
                    sent = 0
                for cue in cues[sent:]:
                    yield format_sse("cue", cue)
                sent = len(cues)
                marker = (
                    status["estado"],
                    status["pendiente"],
                    status["error"],
                    status["generacion"],
                    status["idioma_detectado"],
                )
                if marker != last_marker:
                    yield format_sse("estado", status)
                    last_marker = marker
                await asyncio.sleep(0.25)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _session_dir(settings: Settings, session_id: str, generation: int) -> Path:
    path = settings.work_dir / "sesiones" / session_id / f"gen-{generation}"
    path.mkdir(parents=True, exist_ok=True)
    return path
