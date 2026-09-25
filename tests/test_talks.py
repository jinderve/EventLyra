from fastapi.testclient import TestClient

from eventlyra.config import Settings
from eventlyra.server.app import create_app
from services.live_engine.sessions import Session, SessionManager
from services.live_engine.talks import add_talk, decorate_talks, load_talks, update_talk


def test_defaults_son_las_dos_charlas_de_nerdearla():
    talks = load_talks()
    assert [item["id"] for item in talks[:2]] == [
        "salatino-feedback",
        "tanenbaum-interview",
    ]
    assert talks[0]["youtube_url"].endswith("37oDPQGB8Ww")
    assert talks[1]["youtube_url"].endswith("d567RerxDGk")
    assert talks[0]["image_url"]
    assert talks[0]["tags"]


def test_k_dos_recibe_las_defaults_en_los_canales():
    manager = SessionManager(2)
    manager.apply_talks(load_talks())
    first = manager.get("1")
    second = manager.get("2")
    assert first is not None and "feedback" in (first.title or "").lower()
    assert first.source_lang == "es"
    assert first.target_lang == "en"
    assert first.youtube_url
    assert second is not None
    assert second.source_lang == "en"
    assert second.target_lang == "es"


def test_talk_extra_no_inventa_canal_gpu(tmp_path):
    add_talk(tmp_path, {"title": "Extra talk", "tags": "ai, community", "speakers": "Ada"})
    talks = load_talks(tmp_path)
    assert len(talks) == 3
    decorated = decorate_talks(talks, k=2, sessions=[{"id": "1", "status": "ready"}])
    assert decorated[0]["channel_id"] == "1"
    assert decorated[2]["channel_id"] is None
    assert decorated[2]["live"] is False


def test_watchers_no_bajan_de_cero():
    session = Session(id="1")
    session.remove_watcher()
    assert session.watchers == 0
    session.add_watcher()
    session.add_watcher()
    session.remove_watcher()
    assert session.watchers == 1
    assert session.to_dict()["watchers"] == 1


def test_api_talks_defaults_y_extra_sin_canal(tmp_path):
    app = create_app(
        Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    )
    with TestClient(app) as client:
        listed = client.get("/api/talks").json()
        assert [item["id"] for item in listed["talks"][:2]] == [
            "salatino-feedback",
            "tanenbaum-interview",
        ]
        session = client.get("/api/sessions/1").json()
        assert "feedback" in session["title"].lower()
        assert session["youtube_url"]
        created = client.post(
            "/api/talks",
            json={"title": "Community room", "tags": "ai", "speakers": "Ada"},
        )
        assert created.status_code == 200
        body = created.json()
        assert body["channel_id"] is None
        assert any(item["id"].startswith("community-room") for item in body["talks"])
        event = client.get("/api/event").json()
        assert len(event["talks"]) == 3
        assert event["talks"][2]["channel_id"] is None
        assert event["talks"][0]["published"] is True
        assert event["talks"][2]["published"] is False


def test_update_and_publish_talk(tmp_path):
    add_talk(tmp_path, {"title": "Extra talk", "youtube_url": "https://youtu.be/abc"})
    talks = load_talks(tmp_path)
    extra = talks[-1]
    updated = update_talk(
        tmp_path,
        extra["id"],
        {"title": "Community room", "published": True, "target_lang": "pt"},
    )
    assert updated["title"] == "Community room"
    assert updated["published"] is True
    assert updated["target_lang"] == "pt"
    patched_default = update_talk(
        tmp_path,
        "salatino-feedback",
        {"published": False, "room": "Stream C"},
    )
    assert patched_default["published"] is False
    assert patched_default["room"] == "Stream C"
    reloaded = load_talks(tmp_path)
    assert reloaded[0]["published"] is False
    assert reloaded[0]["room"] == "Stream C"
    assert reloaded[-1]["title"] == "Community room"


def test_api_patch_talk_publish(tmp_path):
    app = create_app(
        Settings(sessions_per_gpu=2, work_dir=tmp_path, load_models=False)
    )
    with TestClient(app) as client:
        patched = client.patch(
            "/api/talks/salatino-feedback",
            json={"published": False, "target_lang": "pt"},
        )
        assert patched.status_code == 200
        assert patched.json()["talk"]["published"] is False
        session = client.get("/api/sessions/1").json()
        assert session["published"] is False
        assert session["target_lang"] == "pt"
