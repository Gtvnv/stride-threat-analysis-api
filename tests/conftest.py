from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import settings
from pytest_socket import disable_socket, enable_socket, socket_allow_hosts

from app.clients.azure_openai_client import AzureOpenAIClient

# Perfil Hypothesis do projeto: mínimo de 100 exemplos por propriedade.
settings.register_profile("default", max_examples=100)
settings.load_profile("default")

AZURE_ENV_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "MAX_IMAGE_SIZE_BYTES",
)

AZURE_ACCESS_FORBIDDEN_MESSAGE = "acesso real ao Azure proibido nos testes"

# Marker de opt-out: testes que constroem AzureOpenAIClient com um sdk_factory fake.
ALLOW_AZURE_CLIENT_INIT_MARKER = "allow_azure_client_init"


def _forbidden_azure_init(self: Any, *args: Any, **kwargs: Any) -> None:
    raise RuntimeError(AZURE_ACCESS_FORBIDDEN_MESSAGE)


@pytest.fixture(autouse=True)
def _isolated_environment(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Rede bloqueada, ambiente do Azure limpo e AzureOpenAIClient real proibido."""
    if sys.platform == "win32":
        # No Windows o asyncio cria o socketpair do event loop com AF_INET em loopback;
        # disable_socket() bloquearia a criação do socket. Só loopback é permitido.
        socket_allow_hosts(["127.0.0.1", "::1"], allow_unix_socket=True)
    else:
        disable_socket(allow_unix_socket=True)
    for name in AZURE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    if request.node.get_closest_marker(ALLOW_AZURE_CLIENT_INIT_MARKER) is None:
        monkeypatch.setattr(AzureOpenAIClient, "__init__", _forbidden_azure_init)
    try:
        yield
    finally:
        enable_socket()


@dataclass(frozen=True)
class RecordedCall:
    prompt: Any
    image: bytes
    media_type: str


class FakeModelClient:
    """ModelClient falso: devolve ``response`` ou levanta ``error``, registrando chamadas."""

    def __init__(self, response: str | None = None, error: BaseException | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[RecordedCall] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    async def complete(self, prompt: Any, image: bytes, media_type: str) -> str:
        self.calls.append(RecordedCall(prompt, image, media_type))
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("FakeModelClient sem resposta configurada")
        return self.response


@pytest.fixture
def fake_model_client() -> FakeModelClient:
    return FakeModelClient()


def assert_error_response(
    response: Any,
    status_code: int,
    code: str,
    *,
    forbidden: tuple[str, ...] = (),
) -> None:
    """Valida o corpo de erro uniforme e que nenhum texto proibido vazou (corpo ou headers)."""
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert "threats" not in body
    haystack = response.text + repr(dict(response.headers))
    for text in forbidden:
        assert text not in haystack


def assert_failure_without_model_call(
    response: Any,
    client: FakeModelClient,
    status_code: int,
    code: str,
    *,
    forbidden: tuple[str, ...] = (),
) -> None:
    """Falha de validação/configuração: erro uniforme e modelo nunca chamado."""
    assert_error_response(response, status_code, code, forbidden=forbidden)
    assert client.call_count == 0
