"""Nenhum segredo (chave, endpoint, mensagens do SDK) vaza em logs, corpo ou headers.

Validates: Requirements 5.5, 6.1, 6.2
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.clients.azure_openai_client import get_model_client
from app.clients.model_client import (
    ModelOutputInvalidError,
    ModelServiceError,
    ModelTimeoutError,
)
from app.core.logging import LOGGER_NAME
from app.main import create_app
from tests.conftest import FakeModelClient

SENTINEL_KEY = "SENTINEL-KEY-9f3a7c1e-do-not-leak"
SENTINEL_ENDPOINT = "https://sentinel-endpoint-4b2d.example.invalid"
SENTINEL_DEPLOYMENT = "sentinel-deployment-8e1c"
SENTINEL_EXC = "SENTINEL-EXC-5d6b-secret-detail"
SECRETS = (SENTINEL_KEY, SENTINEL_ENDPOINT, SENTINEL_DEPLOYMENT, SENTINEL_EXC)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
LONG_CONTEXT = "x" * 2001


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", SENTINEL_ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", SENTINEL_KEY)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", SENTINEL_DEPLOYMENT)
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")


@pytest.fixture
def logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    # O logger da aplicação não propaga; anexa o handler do caplog diretamente.
    app_logger = logging.getLogger(LOGGER_NAME)
    caplog.set_level(logging.DEBUG)
    app_logger.addHandler(caplog.handler)
    old_level = app_logger.level
    app_logger.setLevel(logging.DEBUG)
    try:
        yield caplog
    finally:
        app_logger.removeHandler(caplog.handler)
        app_logger.setLevel(old_level)


def _call(
    fake: FakeModelClient,
    files: dict[str, Any] | None,
    data: dict[str, str] | None = None,
) -> Any:
    app = create_app()
    app.dependency_overrides[get_model_client] = lambda: fake
    client = TestClient(app, raise_server_exceptions=False)
    return client.post("/api/v1/analyze", files=files, data=data)


def _png(name: str = "d.png", content: bytes = PNG, ctype: str = "image/png") -> dict[str, Any]:
    return {"file": (name, content, ctype)}


def _assert_no_secrets(response: Any, caplog: pytest.LogCaptureFixture) -> None:
    haystack = response.text + repr(dict(response.headers))
    log_text = caplog.text + "".join(
        r.getMessage() + repr(r.__dict__.get("args", "")) for r in caplog.records
    )
    for secret in SECRETS:
        assert secret not in haystack, "segredo vazou na resposta"
        assert secret not in log_text, "segredo vazou nos logs"


def _scenarios() -> list[Any]:
    return [
        pytest.param(FakeModelClient(), None, None, 400, id="file_missing"),
        pytest.param(FakeModelClient(), _png(content=b""), None, 400, id="file_empty"),
        pytest.param(
            FakeModelClient(), _png("d.gif", PNG, "image/gif"), None, 415, id="unsupported_type"
        ),
        pytest.param(
            FakeModelClient(), _png("d.png", b"not-a-png-at-all", "image/png"), None, 415,
            id="signature_mismatch",
        ),
        pytest.param(
            FakeModelClient(), _png(), {"context": LONG_CONTEXT}, 422, id="context_too_long"
        ),
        pytest.param(
            FakeModelClient(error=ModelServiceError()), _png(), None, 502, id="upstream_error"
        ),
        pytest.param(
            FakeModelClient(error=ModelOutputInvalidError()), _png(), None, 502,
            id="model_output_invalid_error",
        ),
        pytest.param(
            FakeModelClient(response=f"nao-json {SENTINEL_EXC}"), _png(), None, 502,
            id="model_output_not_json",
        ),
        pytest.param(
            FakeModelClient(error=ModelTimeoutError()), _png(), None, 504, id="upstream_timeout"
        ),
        pytest.param(
            FakeModelClient(error=RuntimeError(f"{SENTINEL_KEY} {SENTINEL_EXC}")),
            _png(), None, 500, id="unhandled_exception",
        ),
    ]


@pytest.mark.parametrize("fake, files, data, status", _scenarios())
def test_failure_scenarios_do_not_leak_secrets(
    env: None,
    logs: pytest.LogCaptureFixture,
    fake: FakeModelClient,
    files: dict[str, Any] | None,
    data: dict[str, str] | None,
    status: int,
) -> None:
    response = _call(fake, files, data)
    assert response.status_code == status
    _assert_no_secrets(response, logs)


def test_too_large_file_does_not_leak_secrets(
    env: None, logs: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_IMAGE_SIZE_BYTES", "10")
    response = _call(FakeModelClient(), _png())
    assert response.status_code == 413
    _assert_no_secrets(response, logs)


def test_invalid_max_image_size_config_does_not_leak_secrets(
    env: None, logs: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAX_IMAGE_SIZE_BYTES", f"abc-{SENTINEL_EXC}")
    response = _call(FakeModelClient(), _png())
    assert response.status_code == 503
    _assert_no_secrets(response, logs)


def test_missing_configuration_does_not_leak_secrets(
    logs: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Chave presente, mas endpoint/deployment/versão ausentes -> 503.
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", SENTINEL_KEY)
    response = _call(FakeModelClient(), _png())
    assert response.status_code == 503
    _assert_no_secrets(response, logs)


def test_default_client_factory_without_config_does_not_leak_secrets(
    logs: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sem override: get_model_client real falha com 503 antes de qualquer acesso externo.
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", SENTINEL_KEY)
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post("/api/v1/analyze", files=_png())
    assert response.status_code == 503
    _assert_no_secrets(response, logs)


def test_response_headers_do_not_contain_secrets(
    env: None, logs: pytest.LogCaptureFixture
) -> None:
    response = _call(FakeModelClient(error=ModelServiceError()), _png())
    assert response.status_code == 502
    for secret in SECRETS:
        assert secret not in repr(dict(response.headers))
