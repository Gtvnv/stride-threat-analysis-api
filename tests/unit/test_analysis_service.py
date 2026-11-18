from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from app.api.errors import AppError
from app.clients.model_client import ModelServiceError, ModelTimeoutError
from app.schemas.threat import HUMAN_REVIEW_NOTICE
from app.services.analysis_service import AnalysisService
from tests.conftest import FakeModelClient

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
MAX_SIZE = 1024
MARKER = "SEGREDO-MARKER-12345"


@dataclass(frozen=True)
class Img:
    content: bytes
    content_type: str | None


def _valid_json(**overrides) -> str:
    data = {
        "components": ["API"],
        "data_flows": ["Cliente -> API"],
        "trust_boundaries": ["Internet"],
        "summary": "Resumo.",
        "threats": [
            {
                "category": "Spoofing",
                "component": "API",
                "description": "Sem autenticação.",
                "severity": "Medium",
                "mitigation": "Exigir autenticação.",
            }
        ],
    }
    data.update(overrides)
    return json.dumps(data)


def _service(client: FakeModelClient) -> AnalysisService:
    return AnalysisService(client, MAX_SIZE)


async def test_valid_flow_calls_model_once_and_returns_report() -> None:
    client = FakeModelClient(response=_valid_json())
    report = await _service(client).analyze(Img(PNG, "image/png"), "contexto")
    assert client.call_count == 1
    assert client.calls[0].image == PNG
    assert client.calls[0].media_type == "image/png"
    assert report.disclaimer == HUMAN_REVIEW_NOTICE
    assert len(report.threats) == 1


async def test_diagram_without_architecture_returns_empty_threats() -> None:
    raw = _valid_json(threats=[], summary="Sem arquitetura identificável.")
    client = FakeModelClient(response=raw)
    report = await _service(client).analyze(Img(PNG, "image/png"), None)
    assert client.call_count == 1
    assert report.threats == []
    assert report.summary == "Sem arquitetura identificável."


@pytest.mark.parametrize("raw", ["isto não é json " + MARKER, '{"summary": "x"}'])
async def test_invalid_model_output_gives_502_with_single_call(raw: str) -> None:
    client = FakeModelClient(response=raw)
    with pytest.raises(AppError) as exc_info:
        await _service(client).analyze(Img(PNG, "image/png"), None)
    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "model_output_invalid"
    assert MARKER not in exc_info.value.message
    assert client.call_count == 1


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ModelServiceError(), 502, "upstream_error"),
        (ModelTimeoutError(), 504, "upstream_timeout"),
    ],
)
async def test_model_error_is_propagated_with_single_call(
    error: AppError, status: int, code: str
) -> None:
    client = FakeModelClient(error=error)
    with pytest.raises(AppError) as exc_info:
        await _service(client).analyze(Img(PNG, "image/png"), None)
    assert exc_info.value is error
    assert (exc_info.value.status_code, exc_info.value.code) == (status, code)
    assert client.call_count == 1


@pytest.mark.parametrize(
    ("image", "status", "code"),
    [
        (Img(PNG, "image/gif"), 415, "unsupported_media_type"),
        (Img(PNG, None), 415, "unsupported_media_type"),
        (Img(b"", "image/png"), 400, "file_empty"),
        (Img(PNG + b"\x00" * MAX_SIZE, "image/png"), 413, "file_too_large"),
        (Img(b"not an image", "image/png"), 415, "signature_mismatch"),
        (Img(PNG, "image/jpeg"), 415, "signature_mismatch"),
    ],
)
async def test_invalid_image_does_not_call_model(image: Img, status: int, code: str) -> None:
    client = FakeModelClient(response=_valid_json())
    with pytest.raises(AppError) as exc_info:
        await _service(client).analyze(image, None)
    assert (exc_info.value.status_code, exc_info.value.code) == (status, code)
    assert client.call_count == 0
