"""Contrato do cliente do modelo e exceções associadas.

Não depende do SDK do Azure/OpenAI. As exceções são subclasses de AppError e
usam apenas mensagens constantes do catálogo.
"""

from __future__ import annotations

from typing import Protocol

from app.api.errors import AppError
from app.prompts.prompt_builder import PromptMessages


class ModelServiceError(AppError):
    """Falha ao consultar o modelo (HTTP 502, upstream_error)."""

    def __init__(self) -> None:
        super().__init__("upstream_error")


class ModelTimeoutError(AppError):
    """Tempo limite excedido ao consultar o modelo (HTTP 504, upstream_timeout)."""

    def __init__(self) -> None:
        super().__init__("upstream_timeout")


class ModelOutputInvalidError(AppError):
    """Saída do modelo vazia, recusada ou incompleta (HTTP 502, model_output_invalid)."""

    def __init__(self) -> None:
        super().__init__("model_output_invalid")


class ModelClient(Protocol):
    async def complete(self, prompt: PromptMessages, image: bytes, media_type: str) -> str:
        """Retorna o conteúdo textual bruto da resposta do modelo.

        Levanta ModelServiceError, ModelTimeoutError ou ModelOutputInvalidError.
        """
        ...
