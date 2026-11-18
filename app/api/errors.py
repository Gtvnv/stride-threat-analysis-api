"""Tratamento de erros HTTP da API.

Todas as mensagens são constantes. Nenhuma delas interpola texto do Azure,
endpoint, chave, valores enviados pelo cliente ou saída do modelo.
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# código -> (status HTTP, mensagem constante)
ERROR_CATALOG: Final[dict[str, tuple[int, str]]] = {
    "file_missing": (
        400,
        "Arquivo ausente. Envie a imagem na parte 'file' de uma requisição multipart/form-data.",
    ),
    "file_empty": (400, "O arquivo enviado está vazio."),
    "file_too_large": (413, "O arquivo excede o tamanho máximo permitido."),
    "unsupported_media_type": (
        415,
        "Tipo de conteúdo não permitido. Use image/png ou image/jpeg.",
    ),
    "signature_mismatch": (
        415,
        "O conteúdo do arquivo não corresponde ao tipo de imagem declarado.",
    ),
    "context_too_long": (422, "O campo 'context' excede o limite de 2000 caracteres."),
    "invalid_request": (422, "Requisição inválida."),
    "service_not_configured": (503, "Serviço não configurado."),
    "upstream_error": (502, "Falha ao consultar o serviço de análise."),
    "model_output_invalid": (
        502,
        "O serviço de análise retornou uma resposta inválida.",
    ),
    "upstream_timeout": (504, "Tempo limite excedido ao consultar o serviço de análise."),
    "internal_error": (500, "Erro interno."),
}


class AppError(Exception):
    """Erro esperado da aplicação, com status, código e mensagem constantes."""

    status_code: int
    code: str
    message: str

    def __init__(self, code: str) -> None:
        if code not in ERROR_CATALOG:
            code = "internal_error"
        self.code = code
        self.status_code, self.message = ERROR_CATALOG[code]
        super().__init__(code)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Corpo de erro uniforme: {"error": {"code": ..., "message": ...}}."""

    error: ErrorDetail

    @classmethod
    def from_code(cls, code: str) -> "ErrorResponse":
        _, message = ERROR_CATALOG[code]
        return cls(error=ErrorDetail(code=code, message=message))


def _json_error(code: str) -> JSONResponse:
    status_code, _ = ERROR_CATALOG[code]
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse.from_code(code).model_dump(),
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    code = exc.code if isinstance(exc, AppError) else "internal_error"
    logger.info("app_error code=%s", code)
    return _json_error(code)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Não ecoa o valor enviado nem o conteúdo de exc.errors().
    logger.info("app_error code=invalid_request")
    return _json_error("invalid_request")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Registra apenas o tipo da exceção, nunca a mensagem.
    logger.error("unhandled_exception type=%s", type(exc).__name__)
    return _json_error("internal_error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
