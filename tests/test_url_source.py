import pytest

from services.live_engine.sessions import Session
from services.live_engine.url_source import (
    LIVE_CHUNK_SECONDS,
    STREAM_CHUNK_SECONDS,
    VOD_MAX_PENDING,
    UrlSourceError,
    normalize_youtube_url,
    ytdlp_command,
    youtube_video_id,
)


def test_acepta_youtube_y_rechaza_otros():
    assert normalize_youtube_url("https://www.youtube.com/watch?v=abc")
    assert normalize_youtube_url("https://youtu.be/abc")
    assert youtube_video_id("https://youtu.be/abc123") == "abc123"
    assert youtube_video_id("https://www.youtube.com/watch?v=xyz") == "xyz"
    with pytest.raises(UrlSourceError):
        normalize_youtube_url("https://vimeo.com/1")
    with pytest.raises(UrlSourceError):
        normalize_youtube_url("not-a-url")
    assert youtube_video_id("https://www.youtube.com/embed/emb1") == "emb1"
    assert youtube_video_id("https://www.youtube.com/shorts/short1") == "short1"
    assert LIVE_CHUNK_SECONDS == 4.0
    assert STREAM_CHUNK_SECONDS == 4.0
    assert LIVE_CHUNK_SECONDS < 8.0
    assert VOD_MAX_PENDING == 6


def test_youtube_live_expone_delay_medido():
    session = Session(id="1")
    session.begin()
    session.set_playback(kind="youtube", youtube_id="abc", is_live=True)
    session.configure_live(LIVE_CHUNK_SECONDS)
    session.mark_live_origin(1_000.0, LIVE_CHUNK_SECONDS)
    session.last_latency_ms = 3500
    session.last_queue_wait_ms = 200
    playback = session.to_dict()["playback"]
    assert playback["is_live"] is True
    assert playback["chunk_seconds"] == 4.0
    assert playback["stream_origin_at"] == 1_000.0
    assert playback["delay_sec"] == round(4.0 + 3.5 + 0.2 + 0.8, 2)


def test_youtube_vod_no_expone_delay():
    session = Session(id="1")
    session.set_playback(kind="youtube", youtube_id="abc", is_live=False)
    assert session.to_dict()["playback"]["delay_sec"] is None
    assert session.to_dict()["playback"]["is_live"] is False
    assert session.to_dict()["playback"]["ready_until"] == 0.0


def test_ready_until_sigue_el_ultimo_cue():
    from services.live_engine.types import Cue

    session = Session(id="1")
    session.cues.append(
        Cue(0.0, 4.2, "a", "b", "es", "en"),
    )
    session.cues.append(
        Cue(4.0, 8.1, "c", "d", "es", "en"),
    )
    assert session.to_dict()["playback"]["ready_until"] == 8.1


def test_ytdlp_se_resuelve_sin_exigir_path():
    try:
        command = ytdlp_command()
    except UrlSourceError as exc:
        assert "pip install yt-dlp" in str(exc)
        return
    assert command[0]
    assert "-m" in command or "yt-dlp" in command[0].lower()
