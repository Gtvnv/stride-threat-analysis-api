"""Implementação do ``ModelClient`` sobre o Azure OpenAI (SDK ``openai`` v1+).

Único módulo que depende do SDK. Mensagens originais de exceções do SDK nunca
são repassadas nem encadeadas.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Callable, Final

from openai import AsyncAzureOpenAI

from app.clients.model_client import (
    ModelOutputInvalidError,
    ModelServiceError,
    ModelTimeoutError,
)
from app.core.settings import ReadySettings, Settings
from app.prompts.prompt_builder import PromptMessages

REQUEST_TIMEOUT_SECONDS: Final = 60
TEMPERATURE: Final = 0.1
MAX_TOKENS: Final = 4096

SdkFactory = Callable[..., Any]


class AzureOpenAIClient:
    """Cliente do modelo via ``AsyncAzureOpenAI`` (sem retentativas do SDK)."""

    def __init__(
        self,
        settings: ReadySettings,
        sdk_factory: SdkFactory | None = None,
    ) -> None:
        factory = sdk_factory if sdk_factory is not None else AsyncAzureOpenAI
        self._deployment = settings.deployment
        self._sdk = factory(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    async def complete(self, prompt: PromptMessages, image: bytes, media_type: str) -> str:
        data_url = f"data:{media_type};base64,{base64.b64encode(image).decode('ascii')}"
        messages = [
            {"role": "system", "content": prompt.system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt.user_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await self._sdk.chat.completions.create(
                    model=self._deployment,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
        except TimeoutError:
            raise ModelTimeoutError() from None
        except Exception:
            raise ModelServiceError() from None

        try:
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message
            content = message.content
            refusal = getattr(message, "refusal", None)
        except Exception:
            raise ModelOutputInvalidError() from None

        if (
            finish_reason != "stop"
            or refusal
            or not isinstance(content, str)
            or not content.strip()
        ):
            raise ModelOutputInvalidError()
        return content


def get_model_client() -> AzureOpenAIClient:
    """Fábrica (dependência FastAPI): lê o ambiente e levanta 503 se incompleto."""
    return AzureOpenAIClient(Settings.from_env().ensure_ready())
