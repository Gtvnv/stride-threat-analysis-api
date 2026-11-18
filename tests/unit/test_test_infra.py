"""A infraestrutura de testes bloqueia rede externa e o cliente Azure real.

Validates: Requirements 5.5, 6.1, 6.2
"""

from __future__ import annotations

import os
import socket

import pytest

from app.clients.azure_openai_client import AzureOpenAIClient
from app.core.settings import ReadySettings
from tests.conftest import (
    ALLOW_AZURE_CLIENT_INIT_MARKER,
    AZURE_ACCESS_FORBIDDEN_MESSAGE,
    AZURE_ENV_VARS,
)

READY = ReadySettings(
    endpoint="https://example.invalid",
    api_key="k",
    deployment="d",
    api_version="v",
    max_image_size=1024,
)


def test_external_socket_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("93.184.216.34", 443))
        finally:
            sock.close()


def test_external_dns_resolution_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError):
        socket.create_connection(("example.com", 443), timeout=1)


def test_real_azure_client_cannot_be_instantiated() -> None:
    with pytest.raises(RuntimeError, match=AZURE_ACCESS_FORBIDDEN_MESSAGE):
        AzureOpenAIClient(READY)


def test_azure_env_vars_are_cleared() -> None:
    for name in AZURE_ENV_VARS:
        assert name not in os.environ


@pytest.mark.allow_azure_client_init
def test_marker_allows_client_with_fake_sdk_factory() -> None:
    assert ALLOW_AZURE_CLIENT_INIT_MARKER == "allow_azure_client_init"
    created: dict[str, object] = {}

    def factory(**kwargs: object) -> object:
        created.update(kwargs)
        return object()

    AzureOpenAIClient(READY, sdk_factory=factory)
    assert created["max_retries"] == 0
