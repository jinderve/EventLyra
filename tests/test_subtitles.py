from eventlyra.engine.subtitles import cues_to_srt, cues_to_txt, cues_to_vtt, render_export


CUES = [
    {
        "inicio": 0.0,
        "fin": 1.2,
        "original": "hello friends",
        "traduccion": "hola amigos",
    },
    {
        "inicio": 1.2,
        "fin": 2.0,
        "original": "second",
        "traduccion": "segunda",
    },
]


def test_srt_tiene_dos_indices():
    srt = cues_to_srt(CUES)
    assert srt.startswith("1\n")
    assert "00:00:00,000 --> 00:00:01,200" in srt
    assert "\n2\n" in srt
    assert "hola amigos" in srt


def test_vtt_empieza_con_webvtt():
    vtt = cues_to_vtt(CUES)
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:01.200" in vtt


def test_txt_y_fmt_invalido():
    txt = cues_to_txt(CUES)
    assert txt.startswith("[00:00:00,000]")
    cuerpo, media, nombre = render_export(CUES, "srt")
    assert nombre.endswith(".srt")
    assert "text/" in media
    assert "1\n" in cuerpo
    try:
        render_export(CUES, "pdf")
        raise AssertionError("tenía que fallar")
    except ValueError as exc:
        assert "fmt" in str(exc)