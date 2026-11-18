"""Testes unitários de configuração (Requirements 5.1, 5.4, 5.5, 5.8)."""

import pytest

from app.api.errors import AppError
from app.core.settings import (
    DEFAULT_MAX_IMAGE_SIZE,
    ENV_API_KEY,
    ENV_API_VERSION,
    ENV_DEPLOYMENT,
    ENV_ENDPOINT,
    ENV_MAX_IMAGE_SIZE,
    Settings,
    parse_max_image_size,
)

KEY = "chave-ultra-secreta-987"


def _settings(**overrides) -> Settings:
    data = {
        "endpoint": "https://x.openai.azure.com",
        "api_key": KEY,
        "deployment": "dep",
        "api_version": "2024-02-01",
        "max_image_size_raw": None,
    }
    data.update(overrides)
    return Settings(**data)


def test_default_when_absent():
    assert parse_max_image_size(None) == DEFAULT_MAX_IMAGE_SIZE == 5 * 1024 * 1024


@pytest.mark.parametrize("raw", ["1e3", "-5", "5.0", "0", "20971521", "", "  ", "abc", "+5", "1_000"])
def test_invalid_max_image_size_raises_503(raw):
    with pytest.raises(AppError) as exc:
        parse_max_image_size(raw)
    assert exc.value.status_code == 503


@pytest.mark.parametrize("raw,expected", [("1", 1), ("20971520", 20971520), (" 1000 ", 1000), ("007", 7)])
def test_valid_max_image_size(raw, expected):
    assert parse_max_image_size(raw) == expected


def test_repr_does_not_contain_api_key():
    s = _settings()
    assert KEY not in repr(s)
    ready = s.ensure_ready()
    assert KEY not in repr(ready)
    assert ready.max_image_size == DEFAULT_MAX_IMAGE_SIZE


@pytest.mark.parametrize("field", ["endpoint", "api_key", "deployment", "api_version"])
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_missing_required_setting_raises_503_without_secrets(field, bad):
    with pytest.raises(AppError) as exc:
        _settings(**{field: bad}).ensure_ready()
    assert exc.value.status_code == 503
    assert KEY not in exc.value.message
    assert KEY not in str(exc.value)


def test_invalid_max_size_makes_ensure_ready_fail():
    with pytest.raises(AppError) as exc:
        _settings(max_image_size_raw="0").ensure_ready()
    assert exc.value.code == "service_not_configured"


def test_from_env_reads_variables_and_has_no_defaults(monkeypatch):
    for name in (ENV_ENDPOINT, ENV_API_KEY, ENV_DEPLOYMENT, ENV_API_VERSION, ENV_MAX_IMAGE_SIZE):
        monkeypatch.delenv(name, raising=False)
    empty = Settings.from_env()
    assert (empty.endpoint, empty.api_key, empty.deployment, empty.api_version, empty.max_image_size_raw) == (
        None,
        None,
        None,
        None,
        None,
    )
    with pytest.raises(AppError):
        empty.ensure_ready()

    monkeypatch.setenv(ENV_ENDPOINT, " https://e ")
    monkeypatch.setenv(ENV_API_KEY, KEY)
    monkeypatch.setenv(ENV_DEPLOYMENT, "d")
    monkeypatch.setenv(ENV_API_VERSION, "v")
    monkeypatch.setenv(ENV_MAX_IMAGE_SIZE, "2048")
    ready = Settings.from_env().ensure_ready()
    assert ready.endpoint == "https://e"
    assert ready.max_image_size == 2048
