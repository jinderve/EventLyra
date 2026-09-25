"""Pull public YouTube audio. This is not RTMP and not the official YouTube API."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from eventlyra.config import Settings
from eventlyra.errors import AudioPrepError
from services.live_engine.audio import ffmpeg_executable, prepare_wav, write_pcm_wav
from services.live_engine.jobs import enqueue_wav
from services.live_engine.runtime import SharedRuntime
from services.live_engine.sessions import Session

logger = logging.getLogger(__name__)

# Streamed YouTube (live or VOD) stays shorter than file uploads.
STREAM_CHUNK_SECONDS = 4.0
LIVE_CHUNK_SECONDS = STREAM_CHUNK_SECONDS
AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio/best"
# Keep a VOD buffer without dumping a 27-minute talk into the GPU queue.
VOD_MAX_PENDING = 6

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class UrlSourceError(AudioPrepError):
    """The URL cannot be pulled as a public YouTube source."""


def normalize_youtube_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise UrlSourceError("A YouTube URL is required.")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        raise UrlSourceError("The URL must start with https://.")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise UrlSourceError("Only public youtube.com or youtu.be URLs are accepted.")
    return text


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    parts = [item for item in parsed.path.split("/") if item]
    if host in {"youtu.be", "www.youtu.be"}:
        return parts[0] if parts else None
    if parts and parts[0] in {"embed", "shorts", "live"} and len(parts) > 1:
        return parts[1]
    return parse_qs(parsed.query).get("v", [None])[0]


def ytdlp_command() -> list[str]:
    """Prefer the interpreter module so Windows venvs do not need yt-dlp on PATH."""
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        yt_dlp = None
    if yt_dlp is not None:
        return [sys.executable, "-m", "yt_dlp"]
    scripts = Path(sys.executable).resolve().parent
    for name in ("yt-dlp.exe", "yt-dlp"):
        candidate = scripts / name
        if candidate.is_file():
            return [str(candidate)]
    found = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if found:
        return [found]
    raise UrlSourceError(
        "yt-dlp is not installed in this Python. "
        "In the same environment that runs EventLyra: python -m pip install yt-dlp"
    )


def inspect_youtube(url: str) -> dict:
    command = [
        *ytdlp_command(),
        "--dump-single-json",
        "--no-warnings",
        "--no-playlist",
        url,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise UrlSourceError("yt-dlp is not installed.") from exc
    except subprocess.TimeoutExpired as exc:
        raise UrlSourceError("YouTube inspection timed out.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        raise UrlSourceError(detail[-1] if detail else "YouTube URL could not be read.") from exc
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise UrlSourceError("YouTube metadata was not valid JSON.") from exc


def download_youtube_audio(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    template = dest_dir / "youtube.%(ext)s"
    command = [
        *ytdlp_command(),
        "--no-playlist",
        "--no-warnings",
        "-f",
        AUDIO_FORMAT,
        "-o",
        str(template),
        url,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise UrlSourceError("YouTube download timed out.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        raise UrlSourceError(detail[-1] if detail else "YouTube download failed.") from exc
    matches = sorted(dest_dir.glob("youtube.*"))
    if not matches:
        raise UrlSourceError("YouTube download produced no audio file.")
    return matches[0]


def _read_exact(handle, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        piece = handle.read(remaining)
        if not piece:
            break
        chunks.append(piece)
        remaining -= len(piece)
    return b"".join(chunks)


@dataclass
class UrlPull:
    session_id: str
    generation: int
    stop: threading.Event
    thread: threading.Thread


class UrlSourceRegistry:
    """One puller per logical session. Stop does not cancel other sessions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pulls: dict[str, UrlPull] = {}

    def stop(self, session_id: str) -> None:
        with self._lock:
            pull = self._pulls.pop(session_id, None)
        if pull is None:
            return
        pull.stop.set()
        pull.thread.join(timeout=5)

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._pulls)
        for session_id in ids:
            self.stop(session_id)

    def start_live(
        self,
        *,
        session: Session,
        url: str,
        settings: Settings,
        runtime: SharedRuntime,
        generation: int,
        work_dir: Path,
    ) -> None:
        session.configure_live(STREAM_CHUNK_SECONDS)
        self.start_stream(
            session=session,
            url=url,
            settings=settings,
            runtime=runtime,
            generation=generation,
            work_dir=work_dir,
        )

    def start_stream(
        self,
        *,
        session: Session,
        url: str,
        settings: Settings,
        runtime: SharedRuntime,
        generation: int,
        work_dir: Path,
    ) -> None:
        self.stop(session.id)
        session.configure_stream(STREAM_CHUNK_SECONDS)
        stop = threading.Event()
        thread = threading.Thread(
            target=self._pull_loop,
            args=(session, url, settings, runtime, generation, work_dir, stop),
            name=f"eventlyra-yt-{session.id}",
            daemon=True,
        )
        with self._lock:
            self._pulls[session.id] = UrlPull(session.id, generation, stop, thread)
        thread.start()

    def _pull_loop(
        self,
        session: Session,
        url: str,
        settings: Settings,
        runtime: SharedRuntime,
        generation: int,
        work_dir: Path,
        stop: threading.Event,
    ) -> None:
        ytdlp = None
        ffmpeg = None
        try:
            ytdlp = subprocess.Popen(
                [
                    *ytdlp_command(),
                    "--no-playlist",
                    "--no-warnings",
                    "-f",
                    AUDIO_FORMAT,
                    "-o",
                    "-",
                    url,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            ffmpeg = subprocess.Popen(
                [
                    ffmpeg_executable(),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    "pipe:0",
                    "-f",
                    "s16le",
                    "-ac",
                    "1",
                    "-ar",
                    str(settings.sample_rate),
                    "pipe:1",
                ],
                stdin=ytdlp.stdout,
                stdout=subprocess.PIPE,
            )
            if ytdlp.stdout is not None:
                ytdlp.stdout.close()
            if ffmpeg.stdout is None:
                raise UrlSourceError("ffmpeg did not open a live audio pipe.")
            chunk_seconds = STREAM_CHUNK_SECONDS
            chunk_bytes = int(settings.sample_rate * chunk_seconds) * 2
            offset = 0.0
            index = 0
            while not stop.is_set():
                if not session.youtube_is_live:
                    while not stop.is_set():
                        with session.lock:
                            pending = session.pending
                        if pending < VOD_MAX_PENDING:
                            break
                        time.sleep(0.2)
                    if stop.is_set():
                        break
                if session.youtube_is_live and session.stream_origin_at is None:
                    session.mark_live_origin(time.time(), chunk_seconds)
                pcm = _read_exact(ffmpeg.stdout, chunk_bytes)
                if len(pcm) < int(settings.sample_rate * 0.3) * 2:
                    break
                prefix = "live" if session.youtube_is_live else "vod"
                wav_path = work_dir / f"{prefix}-{index:04d}.wav"
                write_pcm_wav(wav_path, pcm, settings.sample_rate)
                enqueue_wav(
                    session,
                    wav_path,
                    settings,
                    runtime,
                    generation,
                    offset,
                    chunk_seconds=chunk_seconds,
                )
                offset += chunk_seconds
                index += 1
        except Exception as exc:
            logger.exception("YouTube pull failed for session %s", session.id)
            session.fail_if_current(generation, str(exc))
        finally:
            stop.set()
            for process in (ffmpeg, ytdlp):
                if process is None:
                    continue
                process.terminate()
                try:
                    process.wait(timeout=3)
                except Exception:
                    process.kill()
            with self._lock:
                current = self._pulls.get(session.id)
                if current is not None and current.generation == generation:
                    self._pulls.pop(session.id, None)
            time.sleep(0)
