from eventlyra.engine.agenda import canales_para_k, language_code, load_cache


def test_language_code_english_spanish():
    assert language_code("English") == "en"
    assert language_code("Spanish") == "es"
    assert language_code("Portuguese") == "pt"


def test_cache_mapea_k_canales():
    cache = load_cache()
    canales = canales_para_k(cache, 2)
    assert [item["id"] for item in canales] == ["1", "2"]
    assert canales[0]["titulo"]
    assert canales[0]["idioma"] == "en"
    assert canales[1]["idioma"] == "es"


def test_sin_cache_hay_titulos_genericos(tmp_path):
    canales = canales_para_k({"edition": {}, "sessions": []}, 2)
    assert canales[0]["titulo"] == "Session 1"
    assert canales[1]["id"] == "2"