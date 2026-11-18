"""Testes unitários do AzureOpenAIClient com SDK falso.

Valida: Requirements 3.6, 3.7, 5.6, 5.7.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.clients import azure_openai_client as module
from app.clients.azure_openai_client import AzureOpenAIClient
from app.clients.model_client import (
    ModelOutputInvalidError,
    ModelServiceError,
    ModelTimeoutError,
)
from app.core.settings import ReadySettings
from app.prompts.prompt_builder import PromptMessages

pytestmark = pytest.mark.allow_azure_client_init

MARKER = "SEGREDO-MARCADOR-XYZ"


def _settings() -> ReadySettings:
    return ReadySettings(
        endpoint="https://example.invalid",
        api_key="k",
        deployment="dep",
        api_version="2024-06-01",
        max_image_size=1000,
    )


def _response(content: str | None, finish_reason: str = "stop", refusal=None):
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)]
    )


class FakeSdk:
    def __init__(self, behavior) -> None:
        self.init_kwargs: dict = {}
        self.calls: list[dict] = []
        self._behavior = behavior
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        return await self._behavior()


def _make(behavior) -> tuple[AzureOpenAIClient, FakeSdk]:
    sdk = FakeSdk(behavior)

    def factory(**kwargs):
        sdk.init_kwargs = kwargs
        return sdk

    return AzureOpenAIClient(_settings(), sdk_factory=factory), sdk


async def _call(client: AzureOpenAIClient) -> str:
    return await client.complete(PromptMessages(system="s", user_text="u"), b"\x89PNG", "image/png")


async def test_request_parameters():
    async def ok():
        return _response('{"a": 1}')

    client, sdk = _make(ok)
    assert await _call(client) == '{"a": 1}'
    call = sdk.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert 0 <= call["temperature"] <= 0.2
    assert sdk.init_kwargs["max_retries"] == 0


async def test_timeout_yields_504(monkeypatch):
    monkeypatch.setattr(module, "REQUEST_TIMEOUT_SECONDS", 0.05)

    async def slow():
        await asyncio.sleep(5)

    client, _ = _make(slow)
    with pytest.raises(ModelTimeoutError) as exc:
        await _call(client)
    assert exc.value.status_code == 504


async def test_sdk_error_yields_502_without_marker():
    async def boom():
        raise RuntimeError(MARKER)

    client, _ = _make(boom)
    with pytest.raises(ModelServiceError) as exc:
        await _call(client)
    err = exc.value
    assert err.status_code == 502
    assert MARKER not in str(err)
    assert MARKER not in repr(err)
    assert MARKER not in err.message
    assert err.__cause__ is None


@pytest.mark.parametrize(
    "content, finish_reason",
    [('{"a": 1}', "length"), ("", "stop"), ("   ", "stop"), (None, "stop")],
)
async def test_invalid_output(content, finish_reason):
    async def resp():
        return _response(content, finish_reason)

    client, _ = _make(resp)
    with pytest.raises(ModelOutputInvalidError) as exc:
        await _call(client)
    assert exc.value.status_code == 502
