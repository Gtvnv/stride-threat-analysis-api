"""Orquestração da análise: valida a imagem, monta o prompt, chama o modelo e valida a saída.

Este módulo não importa ``fastapi``. A imagem é descrita por um Protocol estrutural
mínimo, satisfeito por ``app.api.upload.UploadedImage``.
"""

from __future__ import annotations

from typing import Protocol

from app.clients.model_client import ModelClient
from app.prompts.prompt_builder import build_prompt
from app.schemas.threat import ThreatReport
from app.services.image_validator import validate_image
from app.services.response_validator import validate_model_output


class ImageLike(Protocol):
    @property
    def content(self) -> bytes: ...

    @property
    def content_type(self) -> str | None: ...


class AnalysisService:
    def __init__(self, client: ModelClient, max_image_size: int) -> None:
        self._client = client
        self._max_image_size = max_image_size

    async def analyze(self, image: ImageLike, context: str | None) -> ThreatReport:
        """Executa a sequência completa, com no máximo uma chamada ao modelo.

        Qualquer falha de validação (imagem ou saída do modelo) levanta AppError e
        interrompe o fluxo; não há nova tentativa junto ao modelo.
        """
        validate_image(image.content, image.content_type, self._max_image_size)
        prompt = build_prompt(context)
        # Após validate_image, o tipo declarado é PNG ou JPEG (sem parâmetros após ';').
        media_type = (image.content_type or "").split(";", 1)[0].strip().lower()
        raw = await self._client.complete(prompt, image.content, media_type)
        return validate_model_output(raw)
