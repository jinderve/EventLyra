"""Configuración: K es obligatorio y el 4B es el único modelo de traducción."""

import pytest

from eventlyra.config import (
    TRANSLATEGEMMA_4B,
    WHISPER_COMPUTE_INT8_GPU,
    Settings,
    settings_from_argv,
)


def test_cli_exige_k():
    with pytest.raises(SystemExit):
        settings_from_argv([])


def test_cli_toma_k_y_puede_arrancar_sin_modelos(tmp_path):
    settings = settings_from_argv(
        ["--sessions-per-gpu", "2", "--sin-modelos", "--work-dir", str(tmp_path)]
    )
    assert settings.sessions_per_gpu == 2
    assert settings.load_models is False
    assert settings.translation_model_id == TRANSLATEGEMMA_4B
    assert settings.whisper_compute_type == WHISPER_COMPUTE_INT8_GPU


def test_k_menor_que_uno_se_rechaza():
    with pytest.raises(ValueError):
        Settings(sessions_per_gpu=0).validate()


def test_se_rechaza_translategemma_grande():
    with pytest.raises(ValueError):
        Settings(
            sessions_per_gpu=2,
            translation_model_id="google/translategemma-27b-it",
        ).validate()
