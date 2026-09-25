from eventlyra.engine.glossary import aplicar_glosario


def test_glosario_corrige_nombres():
    texto = "En nerdearla usamos jemma junto a cuda y faster whisper en event lyra."
    salida = aplicar_glosario(texto)
    assert "Nerdearla" in salida
    assert "Gemma" in salida
    assert "CUDA" in salida
    assert "faster-whisper" in salida
    assert "EventLyra" in salida


def test_glosario_no_pisa_acentos():
    frase = "Universidad de Córdoba. Soy docente."
    assert aplicar_glosario(frase) == frase