"""EventLyra HTTP API, realtime stream, and web application host."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from eventlyra import __version__
from eventlyra.config import Settings
from services.live_engine.agenda import channels_for_k, load_cache
from services.live_engine.talks import add_talk, decorate_talks, load_talks, update_talk
from services.live_engine.audio import prepare_wav, resample_pcm16, write_pcm_wav
from services.live_engine.jobs import enqueue_wav
from services.live_engine.loader import build_local_runtime
from services.live_engine.runtime import SharedRuntime, instance_id
from services.live_engine.sessions import (
    SOURCE_LANGUAGES,
    TARGET_LANGUAGES,
    Session,
    SessionManager,
)
from services.live_engine.subtitles import render_export
from services.live_engine.url_source import (
    STREAM_CHUNK_SECONDS,
    UrlSourceError,
    UrlSourceRegistry,
    inspect_youtube,
    normalize_youtube_url,
    youtube_video_id,
)
from eventlyra.errors import AudioPrepError

ROOT_DIR = Path(__file__).resolve().parents[2]
LEGACY_STATIC_DIR = ROOT_DIR / "eventlyra" / "server" / "static"
WEB_DIST_DIR = ROOT_DIR / "apps" / "web" / "dist"
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
VIDEO_SUFFIXES = {".mp4", ".webm", ".mkv", ".mov"}
MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
MODELS_UNAVAILABLE_MESSAGE = (
    "Models are not loaded in this process. "
    "On the GPU machine, run scripts/setup-windows.ps1 and start without --sin-modelos."
)
MENSAJE_SIN_MODELOS = MODELS_UNAVAILABLE_MESSAGE


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
        app.state.url_sources.stop_all()
        if app.state.runtime is not None:
            app.state.runtime.stop()

    app = FastAPI(title="EventLyra", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = SessionManager(settings.sessions_per_gpu)
    app.state.runtime = runtime
    app.state.url_sources = UrlSourceRegistry()
    agenda = load_cache()
    app.state.agenda = agenda
    talks = load_talks(settings.work_dir)
    app.state.talks = talks
    app.state.sessions.apply_talks(talks)

    def require_session(session_id: str) -> Session:
        session = app.state.sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Session {session_id} does not exist in this process. "
                    f"K = {settings.sessions_per_gpu}. "
                    "Increase K or run another API instance on another GPU."
                ),
            )
        return session

    def require_runtime() -> SharedRuntime:
        current = app.state.runtime
        if current is None:
            raise HTTPException(status_code=503, detail=MODELS_UNAVAILABLE_MESSAGE)
        return current

    def web_file(name: str) -> Path:
        built = WEB_DIST_DIR / name
        return built if built.is_file() else LEGACY_STATIC_DIR / name

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_file("index.html"))

    @app.get("/overlay")
    def overlay() -> FileResponse:
        return FileResponse(LEGACY_STATIC_DIR / "overlay.html")

    @app.get("/legacy")
    def legacy_player() -> FileResponse:
        return FileResponse(LEGACY_STATIC_DIR / "index.html")

    @app.get("/production")
    @app.get("/produccion", include_in_schema=False)
    def production_page() -> FileResponse:
        return FileResponse(LEGACY_STATIC_DIR / "produccion.html")

    @app.get("/api/health")
    def health() -> dict:
        current = app.state.runtime
        loaded = current is not None
        data = {
            "ok": True,
            "version": __version__,
            "models_loaded": loaded,
            "shared_weights": loaded,
            "sessions_per_gpu": settings.sessions_per_gpu,
            "translation_provider": settings.translator_provider,
            "asr_model": settings.whisper_model,
            "asr_quantization": settings.whisper_compute_type,
            "translation_model": settings.translation_model_id,
            "translation_quantization": settings.translation_quantization,
            "chunk_seconds": settings.chunk_seconds,
            "asr_id": instance_id(current.asr) if loaded else None,
            "translator_id": instance_id(current.translator) if loaded else None,
            "message": None if loaded else MODELS_UNAVAILABLE_MESSAGE,
        }
        data.update(
            {
                "modelos_cargados": data["models_loaded"],
                "pesos_compartidos": data["shared_weights"],
                "proveedor_traduccion": data["translation_provider"],
                "modelo_asr": data["asr_model"],
                "cuantizacion_asr": data["asr_quantization"],
                "modelo_traduccion": data["translation_model"],
                "cuantizacion_traduccion": data["translation_quantization"],
                "mensaje": data["message"],
            }
        )
        return data

    @app.get("/api/sessions")
    def list_sessions() -> dict:
        sessions = app.state.sessions.list_dicts()
        return {
            "sessions_per_gpu": settings.sessions_per_gpu,
            "sessions": sessions,
            "sesiones": sessions,
        }

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str) -> dict:
        return require_session(session_id).to_dict()

    @app.patch("/api/sessions/{session_id}")
    async def update_session(session_id: str, request: Request) -> dict:
        session = require_session(session_id)
        body = await request.json()
        source = body.get("source_lang", body.get("idioma_origen", session.source_lang))
        target = body.get("target_lang", body.get("idioma_destino", session.target_lang))
        if source not in SOURCE_LANGUAGES or target not in TARGET_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail="source_lang accepts auto, es, en, or pt; target_lang accepts es, en, or pt.",
            )
        session.set_languages(source, target)
        if "title" in body or "titulo" in body or "room" in body or "sala" in body:
            session.set_meta(
                title=body.get("title", body.get("titulo")),
                room=body.get("room", body.get("sala")),
            )
        return session.to_dict()

    @app.post("/api/sessions/{session_id}/reset")
    @app.post("/api/sessions/{session_id}/reiniciar", include_in_schema=False)
    def reset_session(session_id: str) -> dict:
        session = require_session(session_id)
        app.state.url_sources.stop(session_id)
        session.begin(status="ready")
        return session.to_dict()

    @app.post("/api/sessions/{session_id}/stop")
    def stop_session(session_id: str) -> dict:
        session = require_session(session_id)
        app.state.url_sources.stop(session_id)
        session.stop_processing()
        return session.to_dict()

    @app.post("/api/sessions/{session_id}/mic")
    def start_microphone(session_id: str) -> dict:
        session = require_session(session_id)
        require_runtime()
        app.state.url_sources.stop(session_id)
        generation = session.begin_microphone()
        return {"generation": generation, **session.to_dict()}

    @app.post("/api/sessions/{session_id}/file")
    @app.post("/api/sessions/{session_id}/archivo", include_in_schema=False)
    async def upload_file(
        session_id: str,
        file: UploadFile | None = File(default=None),
        archivo: UploadFile | None = File(default=None),
    ) -> dict:
        upload = file or archivo
        if upload is None:
            raise HTTPException(status_code=400, detail="A file is required.")
        session = require_session(session_id)
        runtime = require_runtime()
        filename = upload.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail="File must be supported audio or video (wav, mp3, m4a, mp4, webm, mkv).",
            )
        app.state.url_sources.stop(session_id)
        generation = session.begin()
        directory = _session_dir(settings, session_id, generation)
        upload_path = directory / f"input{suffix}"
        try:
            with upload_path.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            if upload_path.stat().st_size == 0:
                raise AudioPrepError("File is empty.")
            wav_path = directory / "source.wav"

            def prepare() -> int:
                prepare_wav(upload_path, wav_path, settings.sample_rate)
                kind = "video" if suffix in VIDEO_SUFFIXES else "audio"
                session.set_playback(
                    kind=kind,
                    path=upload_path,
                    content_type=MEDIA_TYPES.get(suffix) or upload.content_type,
                )
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
            session.fail_if_current(generation, "Audio preparation failed.")
            raise HTTPException(status_code=500, detail="Audio preparation failed.") from exc
        return {
            "chunks": count,
            "generation": generation,
            "fragmentos": count,
            "generacion": generation,
        }

    @app.post("/api/sessions/{session_id}/pcm")
    async def upload_pcm(
        session_id: str,
        request: Request,
        sample_rate: int,
        start: float | None = None,
        inicio: float | None = None,
    ) -> dict:
        session = require_session(session_id)
        runtime = require_runtime()
        offset = 0.0 if start is None and inicio is None else float(start if start is not None else inicio)
        if sample_rate < 8000 or sample_rate > 96000:
            raise HTTPException(status_code=400, detail="sample_rate is out of range.")
        if offset < 0:
            raise HTTPException(status_code=400, detail="start cannot be negative.")
        raw = await request.body()
        if len(raw) < 2:
            raise HTTPException(status_code=400, detail="Audio is empty.")
        generation = session.generation
        if session.playback_kind is None:
            session.set_playback(kind="mic")
        directory = _session_dir(settings, session_id, generation)
        wav_path = directory / f"pcm-{offset:.3f}.wav".replace(":", "-")

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
                offset,
            )

        try:
            count = await asyncio.to_thread(prepare)
        except AudioPrepError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "chunks": count,
            "generation": generation,
            "fragmentos": count,
            "generacion": generation,
        }

    @app.post("/api/sessions/{session_id}/url")
    async def start_url(session_id: str, request: Request) -> dict:
        session = require_session(session_id)
        runtime = require_runtime()
        body = await request.json()
        try:
            url = normalize_youtube_url(body.get("url") or body.get("youtube_url") or "")
        except UrlSourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        generation = session.begin()
        directory = _session_dir(settings, session_id, generation)
        app.state.url_sources.stop(session_id)
        session.set_playback(
            kind="youtube",
            url=url,
            youtube_id=youtube_video_id(url),
            is_live=False,
        )
        app.state.url_sources.start_stream(
            session=session,
            url=url,
            settings=settings,
            runtime=runtime,
            generation=generation,
            work_dir=directory,
        )

        def refine_metadata() -> None:
            try:
                info = inspect_youtube(url)
            except Exception:
                return
            is_live = bool(info.get("is_live")) or info.get("live_status") == "is_live"
            video_id = info.get("id") or youtube_video_id(url)
            session.set_playback(
                kind="youtube",
                url=url,
                youtube_id=str(video_id) if video_id else youtube_video_id(url),
                is_live=is_live,
            )
            if is_live:
                session.configure_live(STREAM_CHUNK_SECONDS)
            title = info.get("title")
            if isinstance(title, str) and title.strip():
                current = session.title
                if current is None or current.startswith("Session "):
                    session.set_meta(title=title.strip())

        asyncio.create_task(asyncio.to_thread(refine_metadata))
        return {
            "mode": "youtube",
            "chunks": 0,
            "generation": generation,
            "fragmentos": 0,
            "generacion": generation,
        }

    @app.get("/api/sessions/{session_id}/stream")
    @app.get("/api/sessions/{session_id}/eventos", include_in_schema=False)
    def session_stream(session_id: str) -> StreamingResponse:
        session = require_session(session_id)

        async def stream():
            session.add_watcher()
            sent = 0
            last_marker = None
            try:
                while True:
                    with session.lock:
                        generation = session.generation
                        cues = [cue.to_dict() for cue in session.cues]
                        status = {
                            "status": session.status,
                            "pending": session.pending,
                            "error": session.error,
                            "generation": generation,
                            "detected_lang": session.detected_lang,
                            "stream_origin_at": session.stream_origin_at,
                        }
                    if sent > len(cues):
                        sent = 0
                    for cue in cues[sent:]:
                        yield format_sse("cue", cue)
                    sent = len(cues)
                    marker = (
                        status["status"],
                        status["pending"],
                        status["error"],
                        status["generation"],
                        status["detected_lang"],
                        status["stream_origin_at"],
                    )
                    if marker != last_marker:
                        legacy_status = {
                            **status,
                            "estado": status["status"],
                            "pendiente": status["pending"],
                            "generacion": status["generation"],
                            "idioma_detectado": status["detected_lang"],
                        }
                        yield format_sse("status", status)
                        yield format_sse("estado", legacy_status)
                        last_marker = marker
                    await asyncio.sleep(0.25)
            finally:
                session.remove_watcher()

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/sessions/{session_id}/media")
    def session_media(session_id: str) -> FileResponse:
        session = require_session(session_id)
        with session.lock:
            path = session.playback_path
            content_type = session.playback_content_type or "application/octet-stream"
            kind = session.playback_kind
        if kind not in {"video", "audio"} or path is None or not path.is_file():
            raise HTTPException(
                status_code=404,
                detail="This session has no playable file. Microphone and YouTube use another player.",
            )
        return FileResponse(path, media_type=content_type, filename=path.name)

    @app.get("/api/sessions/{session_id}/export")
    def export_session(session_id: str, fmt: str = "srt") -> Response:
        session = require_session(session_id)
        with session.lock:
            cues = [cue.to_dict() for cue in session.cues]
        try:
            body, media, filename = render_export(cues, fmt)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return Response(
            content=body.encode("utf-8"),
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/event")
    def event_payload() -> dict:
        cache = app.state.agenda
        edition = cache.get("edition") or {}
        return {
            "id": edition.get("event_id") or "nerdearla-2026",
            "title": edition.get("name") or "Nerdearla 2026",
            "location": edition.get("location"),
            "timezone": edition.get("timezone"),
            "attribution": edition.get("atribucion")
            or "Public Backstage schedule / Nerdearla Argentina 2026",
            "sessions_per_gpu": settings.sessions_per_gpu,
            "tags": ["Technology", "Open source", "AI"],
            "channels": channels_for_k(cache, settings.sessions_per_gpu),
            "talks": decorate_talks(
                load_talks(settings.work_dir),
                settings.sessions_per_gpu,
                app.state.sessions.list_dicts(),
            ),
        }

    @app.get("/api/talks")
    def list_talks() -> dict:
        talks = decorate_talks(
            load_talks(settings.work_dir),
            settings.sessions_per_gpu,
            app.state.sessions.list_dicts(),
        )
        return {"talks": talks, "sessions_per_gpu": settings.sessions_per_gpu}

    @app.post("/api/talks")
    async def create_talk(request: Request) -> dict:
        body = await request.json()
        try:
            talk = add_talk(settings.work_dir, body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        talks = load_talks(settings.work_dir)
        app.state.talks = talks
        app.state.sessions.apply_talks(talks)
        return {
            "talk": talk,
            "channel_id": str(len(talks)) if len(talks) <= settings.sessions_per_gpu else None,
            "talks": decorate_talks(
                talks,
                settings.sessions_per_gpu,
                app.state.sessions.list_dicts(),
            ),
        }

    @app.patch("/api/talks/{talk_id}")
    async def patch_talk(talk_id: str, request: Request) -> dict:
        body = await request.json()
        try:
            talk = update_talk(settings.work_dir, talk_id, body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        talks = load_talks(settings.work_dir)
        app.state.talks = talks
        app.state.sessions.apply_talks(talks)
        decorated = decorate_talks(
            talks,
            settings.sessions_per_gpu,
            app.state.sessions.list_dicts(),
        )
        current = next((item for item in decorated if item.get("id") == talk_id), talk)
        return {"talk": current, "talks": decorated}

    @app.get("/api/agenda")
    def agenda() -> dict:
        cache = app.state.agenda
        edition = cache.get("edition") or {}
        channels = channels_for_k(cache, settings.sessions_per_gpu)
        return {
            "edition": edition,
            "channels": channels,
            "attribution": edition.get("atribucion")
            or "Public Backstage schedule / Nerdearla Argentina 2026",
            "canales": [
                {
                    **channel,
                    "titulo": channel["title"],
                    "sala": channel["room"],
                    "idioma": channel["language"],
                }
                for channel in channels
            ],
        }

    @app.get("/api/production")
    @app.get("/api/produccion", include_in_schema=False)
    def production() -> dict:
        current = app.state.runtime
        loaded = current is not None
        snap = (
            current.snapshot()
            if loaded
            else {
                "queue_by_session": {},
                "queue_total": 0,
                "last_error": None,
                "last_latency_ms": None,
                "last_cue_at": None,
            }
        )
        sessions = []
        for item in app.state.sessions.list_dicts():
            sid = item["id"]
            queue_by_session = snap.get(
                "queue_by_session", snap.get("cola_por_sesion", {})
            )
            sessions.append(
                {
                    "id": sid,
                    "title": item.get("title"),
                    "room": item.get("room"),
                    "agenda_lang": item.get("agenda_lang"),
                    "source_lang": item["source_lang"],
                    "target_lang": item["target_lang"],
                    "status": item["status"],
                    "pending": item["pending"],
                    "error": item["error"],
                    "detected_lang": item["detected_lang"],
                    "cue_count": len(item["cues"]),
                    "latency_ms": item.get("latency_ms"),
                    "queue_wait_ms": item.get("queue_wait_ms"),
                    "last_cue_at": item.get("last_cue_at"),
                    "queue": queue_by_session.get(sid, 0),
                    "watchers": item.get("watchers") or 0,
                }
            )
        return {
            "ok": True,
            "version": __version__,
            "models_loaded": loaded,
            "sessions_per_gpu": settings.sessions_per_gpu,
            "asr_id": instance_id(current.asr) if loaded else None,
            "translator_id": instance_id(current.translator) if loaded else None,
            "asr_model": settings.whisper_model,
            "translation_model": settings.translation_model_id,
            "translation_quantization": settings.translation_quantization,
            **snap,
            "sessions": sessions,
            "sesiones": sessions,
            "modelos_cargados": loaded,
            "cola_por_sesion": snap.get("queue_by_session", {}),
            "cola_total": snap.get("queue_total", 0),
        }

    @app.get("/setup")
    @app.get("/setup/{rest:path}")
    @app.get("/events")
    @app.get("/events/{rest:path}")
    @app.get("/live")
    @app.get("/watch")
    @app.get("/watch/{session_id}")
    @app.get("/overlay/{session_id}")
    def spa_shell(session_id: str | None = None, rest: str | None = None) -> FileResponse:
        built = WEB_DIST_DIR / "index.html"
        if built.is_file():
            return FileResponse(built)
        return FileResponse(LEGACY_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=LEGACY_STATIC_DIR), name="static")
    assets = WEB_DIST_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    return app


def _session_dir(settings: Settings, session_id: str, generation: int) -> Path:
    path = settings.work_dir / "sessions" / session_id / f"gen-{generation}"
    path.mkdir(parents=True, exist_ok=True)
    return path
