"""Rotas HTTP. Sem texto de prompt: ele vive em ``app/prompts``."""

from __future__ import annotations

from typing import Any, Final

from fastapi import APIRouter, Depends, Request

from app.api.errors import AppError, ErrorResponse
from app.api.upload import read_upload
from app.clients.azure_openai_client import get_model_client
from app.clients.model_client import ModelClient
from app.core.settings import Settings
from app.schemas.threat import ThreatReport
from app.services.analysis_service import AnalysisService

router = APIRouter()

_ANALYZE_REQUEST_BODY: Final[dict[str, Any]] = {
    "required": True,
    "content": {
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["file"],
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": "Imagem do diagrama de arquitetura (PNG ou JPEG).",
                    },
                    "context": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 2000,
                        "description": "Contexto adicional opcional (até 2000 caracteres).",
                    },
                },
            }
        }
    },
}

_ERROR_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    code: {"model": ErrorResponse, "description": description}
    for code, description in {
        400: "Arquivo ausente ou vazio",
        413: "Arquivo acima do tamanho máximo",
        415: "Tipo de imagem não permitido",
        422: "Contexto inválido",
        502: "Falha no serviço de análise ou saída inválida do modelo",
        503: "Serviço não configurado",
        504: "Tempo limite excedido",
    }.items()
}


@router.post(
    "/api/v1/analyze",
    response_model=ThreatReport,
    status_code=200,
    responses=_ERROR_RESPONSES,
    openapi_extra={"requestBody": _ANALYZE_REQUEST_BODY},
    summary="Analisa um diagrama de arquitetura com STRIDE",
)
async def analyze(
    request: Request,
    client: ModelClient = Depends(get_model_client),
) -> ThreatReport:
    # A rota chama ensure_ready() diretamente: o 503 não depende do cliente
    # injetado. Testes que trocam get_model_client por um fake via
    # dependency_overrides devem definir variáveis de ambiente falsas
    # (monkeypatch), senão a rota responde 503.
    ready = Settings.from_env().ensure_ready()
    parsed = await read_upload(request, ready.max_image_size)
    if parsed.image is None:
        raise AppError("file_missing")
    service = AnalysisService(client, ready.max_image_size)
    return await service.analyze(parsed.image, parsed.context)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
