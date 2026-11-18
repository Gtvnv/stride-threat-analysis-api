"""Configuração da aplicação lida exclusivamente de variáveis de ambiente.

Não há valores padrão para endpoint, chave e deployment. Nenhum valor de
configuração é incluído em mensagens de erro ou em ``repr``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Final

from app.api.errors import AppError

ENV_ENDPOINT: Final = "AZURE_OPENAI_ENDPOINT"
ENV_API_KEY: Final = "AZURE_OPENAI_API_KEY"
ENV_DEPLOYMENT: Final = "AZURE_OPENAI_DEPLOYMENT"
ENV_API_VERSION: Final = "AZURE_OPENAI_API_VERSION"
ENV_MAX_IMAGE_SIZE: Final = "MAX_IMAGE_SIZE_BYTES"

DEFAULT_MAX_IMAGE_SIZE: Final = 5_242_880  # 5 MiB
MAX_ALLOWED_IMAGE_SIZE: Final = 20_971_520  # 20 MiB
MIN_ALLOWED_IMAGE_SIZE: Final = 1

_DIGITS = re.compile(r"^[0-9]+$")


def parse_max_image_size(raw: str | None) -> int:
    """Interpreta ``MAX_IMAGE_SIZE_BYTES``.

    Ausente (``None``) retorna o padrão de 5 MiB. Caso contrário exige apenas
    dígitos decimais após ``strip()`` e valor entre 1 e 20.971.520; qualquer
    outro caso levanta ``AppError("service_not_configured")``.
    """
    if raw is None:
        return DEFAULT_MAX_IMAGE_SIZE
    text = raw.strip()
    if not _DIGITS.fullmatch(text):
        raise AppError("service_not_configured")
    value = int(text)
    if not MIN_ALLOWED_IMAGE_SIZE <= value <= MAX_ALLOWED_IMAGE_SIZE:
        raise AppError("service_not_configured")
    return value


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


@dataclass(frozen=True)
class ReadySettings:
    """Configuração validada, pronta para uso."""

    endpoint: str
    api_key: str = field(repr=False)
    deployment: str
    api_version: str
    max_image_size: int


@dataclass(frozen=True)
class Settings:
    """Configuração bruta lida do ambiente (sem defaults de credenciais)."""

    endpoint: str | None
    api_key: str | None = field(repr=False)
    deployment: str | None
    api_version: str | None
    max_image_size_raw: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            endpoint=env.get(ENV_ENDPOINT),
            api_key=env.get(ENV_API_KEY),
            deployment=env.get(ENV_DEPLOYMENT),
            api_version=env.get(ENV_API_VERSION),
            max_image_size_raw=env.get(ENV_MAX_IMAGE_SIZE),
        )

    def ensure_ready(self) -> ReadySettings:
        """Valida a configuração; levanta ``AppError`` 503 se incompleta ou inválida."""
        if (
            _is_blank(self.endpoint)
            or _is_blank(self.api_key)
            or _is_blank(self.deployment)
            or _is_blank(self.api_version)
        ):
            raise AppError("service_not_configured")
        max_size = parse_max_image_size(self.max_image_size_raw)
        assert self.endpoint is not None
        assert self.api_key is not None
        assert self.deployment is not None
        assert self.api_version is not None
        return ReadySettings(
            endpoint=self.endpoint.strip(),
            api_key=self.api_key.strip(),
            deployment=self.deployment.strip(),
            api_version=self.api_version.strip(),
            max_image_size=max_size,
        )
