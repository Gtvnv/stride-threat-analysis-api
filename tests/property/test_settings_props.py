"""Testes de propriedade para a configuração (settings)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.api.errors import AppError
from app.core.settings import (
    DEFAULT_MAX_IMAGE_SIZE,
    MAX_ALLOWED_IMAGE_SIZE,
    parse_max_image_size,
)

_WS = st.text(alphabet=" \t\n\r", max_size=3)
_STRICT = re.compile(r"^[0-9]+$")


def _expect_503(raw: str) -> None:
    with pytest.raises(AppError) as exc_info:
        parse_max_image_size(raw)
    assert exc_info.value.status_code == 503


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
def test_absent_value_returns_default() -> None:
    assert parse_max_image_size(None) == DEFAULT_MAX_IMAGE_SIZE == 5_242_880


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@settings(max_examples=100)
@given(
    value=st.integers(min_value=1, max_value=MAX_ALLOWED_IMAGE_SIZE),
    prefix=_WS,
    suffix=_WS,
)
def test_valid_decimal_integer_is_returned(value: int, prefix: str, suffix: str) -> None:
    assert parse_max_image_size(f"{prefix}{value}{suffix}") == value


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@settings(max_examples=100)
@given(value=st.integers(min_value=MAX_ALLOWED_IMAGE_SIZE + 1, max_value=10**15))
def test_value_above_limit_signals_503(value: int) -> None:
    _expect_503(str(value))


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@settings(max_examples=100)
@given(zeros=st.integers(min_value=1, max_value=5))
def test_zero_signals_503(zeros: int) -> None:
    _expect_503("0" * zeros)


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@settings(max_examples=100)
@given(raw=st.text(max_size=20))
def test_arbitrary_string_matches_oracle(raw: str) -> None:
    text = raw.strip()
    valid = bool(_STRICT.fullmatch(text)) and 1 <= int(text) <= MAX_ALLOWED_IMAGE_SIZE
    if valid:
        assert parse_max_image_size(raw) == int(text)
    else:
        _expect_503(raw)


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@settings(max_examples=100)
@given(
    value=st.integers(min_value=1, max_value=MAX_ALLOWED_IMAGE_SIZE),
    form=st.sampled_from(["-{v}", "+{v}", "{v}.0", "{v}e0", "{v}_0", "0x{v}", "{v} 1", "{v},0"]),
)
def test_non_decimal_forms_signal_503(value: int, form: str) -> None:
    _expect_503(form.format(v=value))


# Feature: stride-threat-analysis-api, Property 11
# **Validates: Requirements 5.8**
@pytest.mark.parametrize("raw", ["", "   ", "1e3", "-5", "5.0", "0", "20971521", "abc"])
def test_documented_rejected_examples(raw: str) -> None:
    _expect_503(raw)


# ---------------------------------------------------------------------------
# Property 12: configuração incompleta resulta em 503 sem chamada ao modelo
# ---------------------------------------------------------------------------

_REQUIRED_ENV = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
)
_VALID_VALUES = {
    "AZURE_OPENAI_ENDPOINT": "https://secret-endpoint-xyz.openai.azure.com",
    "AZURE_OPENAI_API_KEY": "secret-key-abc123",
    "AZURE_OPENAI_DEPLOYMENT": "secret-deployment-gpt",
    "AZURE_OPENAI_API_VERSION": "2099-01-01-secret",
}
# Valor inválido: None = variável ausente; "" ou só espaços.
_BAD_VALUE = st.one_of(
    st.none(), st.just(""), st.text(alphabet=" \t\r\n", min_size=1, max_size=5)
)


# Feature: stride-threat-analysis-api, Property 12
# **Validates: Requirements 5.4**
@settings(max_examples=100, deadline=None)
@given(
    bad=st.dictionaries(
        keys=st.sampled_from(_REQUIRED_ENV),
        values=_BAD_VALUE,
        min_size=1,
        max_size=len(_REQUIRED_ENV),
    )
)
def test_incomplete_config_returns_503_without_model_call(bad: dict) -> None:
    import os
    from unittest import mock

    from fastapi.testclient import TestClient

    from app.clients.azure_openai_client import get_model_client
    from app.main import create_app
    from tests.conftest import FakeModelClient

    env = dict(_VALID_VALUES)
    for name, value in bad.items():
        if value is None:
            env.pop(name)
        else:
            env[name] = value

    fake = FakeModelClient(response="{}")
    app = create_app()
    app.dependency_overrides[get_model_client] = lambda: fake

    with mock.patch.dict(os.environ, env, clear=False):
        for name in bad:
            if bad[name] is None:
                os.environ.pop(name, None)
        client = TestClient(app)
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("d.png", b"\x89PNG\r\n\x1a\n" + b"0" * 16, "image/png")},
        )
        health = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"error"}
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    haystack = response.text + repr(dict(response.headers))
    for name, value in _VALID_VALUES.items():
        assert value not in haystack
        assert name not in haystack
    assert fake.call_count == 0
    assert health.status_code == 200
