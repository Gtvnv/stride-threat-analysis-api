"""Testes de API por cenário de /api/v1/analyze, /health e /docs."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import pytest_asyncio

from app.clients.azure_openai_client import get_model_client
from app.clients.model_client import (
    ModelOutputInvalidError,
    ModelServiceError,
    ModelTimeoutError,
)
from app.main import create_app
from tests.conftest import (
    FakeModelClient,
    assert_error_response,
    assert_failure_without_model_call,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
MAX_SIZE = 1024

VALID_ANALYSIS: dict[str, Any] = {
    "components": ["API", "Banco"],
    "data_flows": ["API -> Banco"],
    "trust_boundaries": ["Internet / DMZ"],
    "summary": "Aplicação web com banco de dados.",
    "threats": [
        {
            "category": "Tampering",
            "component": "API",
            "description": "Alteração de dados em trânsito.",
            "severity": "High",
            "mitigation": "Usar TLS.",
        }
    ],
}


@pytest.fixture(autouse=True)
def _azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "fake-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    monkeypatch.setenv("MAX_IMAGE_SIZE_BYTES", str(MAX_SIZE))


@pytest.fixture
def fake() -> FakeModelClient:
    return FakeModelClient(response=json.dumps(VALID_ANALYSIS))


@pytest.fixture
def app(fake: FakeModelClient) -> Iterator[Any]:
    application = create_app()
    application.dependency_overrides[get_model_client] = lambda: fake
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _upload(
    content: bytes = PNG, content_type: str = "image/png", context: str | None = None
) -> dict[str, Any]:
    files: dict[str, Any] = {"file": ("diagram", content, content_type)}
    if context is not None:
        files["context"] = (None, context)
    return {"files": files}


async def test_success(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(context="contexto"))
    assert response.status_code == 200
    body = response.json()
    assert body["threats"][0]["category"] == "Tampering"
    assert body["disclaimer"]
    assert fake.call_count == 1


async def test_success_jpeg(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(JPEG, "image/jpeg"))
    assert response.status_code == 200
    assert fake.call_count == 1


async def test_unsupported_media_type(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(PNG, "image/gif"))
    assert_failure_without_model_call(response, fake, 415, "unsupported_media_type")


async def test_file_too_large(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(PNG + b"\x00" * MAX_SIZE))
    assert_failure_without_model_call(response, fake, 413, "file_too_large")


async def test_empty_file(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(b""))
    assert_failure_without_model_call(response, fake, 400, "file_empty")


async def test_signature_mismatch(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", **_upload(JPEG, "image/png"))
    assert_failure_without_model_call(response, fake, 415, "signature_mismatch")


async def test_missing_file(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.post("/api/v1/analyze", files={"context": (None, "x")})
    assert_failure_without_model_call(response, fake, 400, "file_missing")


async def test_invalid_model_json(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    fake.response = "isto não é JSON"
    response = await client.post("/api/v1/analyze", **_upload())
    assert_error_response(response, 502, "model_output_invalid", forbidden=("isto não é JSON",))
    assert fake.call_count == 1


async def test_schema_violation(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    invalid = {**VALID_ANALYSIS, "threats": [{"category": "Nope"}]}
    fake.response = json.dumps(invalid)
    response = await client.post("/api/v1/analyze", **_upload())
    assert_error_response(response, 502, "model_output_invalid")
    assert fake.call_count == 1


async def test_model_output_invalid_error(
    client: httpx.AsyncClient, fake: FakeModelClient
) -> None:
    fake.error = ModelOutputInvalidError()
    response = await client.post("/api/v1/analyze", **_upload())
    assert_error_response(response, 502, "model_output_invalid")


async def test_azure_error(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    fake.error = ModelServiceError()
    response = await client.post("/api/v1/analyze", **_upload())
    assert_error_response(response, 502, "upstream_error", forbidden=("fake-key", "fake.example"))
    assert fake.call_count == 1


async def test_timeout(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    fake.error = ModelTimeoutError()
    response = await client.post("/api/v1/analyze", **_upload())
    assert_error_response(response, 504, "upstream_timeout")
    assert fake.call_count == 1


async def test_context_2000_chars_accepted(
    client: httpx.AsyncClient, fake: FakeModelClient
) -> None:
    response = await client.post("/api/v1/analyze", **_upload(context="a" * 2000))
    assert response.status_code == 200
    assert fake.call_count == 1


async def test_context_2001_chars_rejected(
    client: httpx.AsyncClient, fake: FakeModelClient
) -> None:
    response = await client.post("/api/v1/analyze", **_upload(context="a" * 2001))
    assert_failure_without_model_call(response, fake, 422, "context_too_long")


async def test_docs_available(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.get("/docs")
    assert response.status_code == 200
    assert fake.call_count == 0


async def test_health_does_not_call_model(client: httpx.AsyncClient, fake: FakeModelClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake.call_count == 0


async def test_diagram_without_architecture(
    client: httpx.AsyncClient, fake: FakeModelClient
) -> None:
    empty = {
        "components": [],
        "data_flows": [],
        "trust_boundaries": [],
        "summary": "A imagem não contém uma arquitetura identificável.",
        "threats": [],
    }
    fake.response = json.dumps(empty)
    response = await client.post("/api/v1/analyze", **_upload())
    assert response.status_code == 200
    body = response.json()
    assert body["threats"] == []
    assert body["summary"]
    assert fake.call_count == 1
