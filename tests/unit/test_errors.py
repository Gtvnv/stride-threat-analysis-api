"""Testes unitários do tratamento de erros (Requirements 5.5)."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import ERROR_CATALOG, AppError, ErrorResponse, register_exception_handlers

SECRET = "super-secret-key-123"
ENDPOINT = "https://meu-recurso.openai.azure.com"


@pytest.mark.parametrize("code", list(ERROR_CATALOG))
def test_app_error_maps_code_to_status_and_message(code):
    err = AppError(code)
    status, message = ERROR_CATALOG[code]
    assert (err.status_code, err.message, err.code) == (status, message, code)


def test_unknown_code_falls_back_to_internal_error():
    err = AppError("nope")
    assert err.code == "internal_error"
    assert err.status_code == 500


def test_error_response_shape():
    body = ErrorResponse.from_code("file_empty").model_dump()
    assert body == {"error": {"code": "file_empty", "message": ERROR_CATALOG["file_empty"][1]}}


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    async def app_error():
        raise AppError("service_not_configured")

    @app.get("/boom")
    async def boom():
        raise RuntimeError(f"falha {SECRET} em {ENDPOINT}")

    @app.get("/typed")
    async def typed(n: int):
        return n

    return TestClient(app, raise_server_exceptions=False)


def test_service_not_configured_body_has_no_secrets():
    r = _client().get("/app-error")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_not_configured"


def test_unhandled_exception_returns_generic_500_without_secrets():
    r = _client().get("/boom")
    assert r.status_code == 500
    assert r.json() == ErrorResponse.from_code("internal_error").model_dump()
    blob = r.text + json.dumps(dict(r.headers))
    assert SECRET not in blob
    assert ENDPOINT not in blob


def test_validation_error_does_not_echo_input():
    r = _client().get("/typed", params={"n": "valor-ecoado-xyz"})
    assert r.status_code == 422
    assert "valor-ecoado-xyz" not in r.text
    assert r.json()["error"]["code"] == "invalid_request"
