"""Logs estruturados (JSON) sem segredos nem conteúdo do usuário.

Só campos de uma lista permitida chegam à saída: ``request_id``, código do erro,
duração e metadados não sensíveis. Nunca são registrados ``api_key``, bytes da
imagem, ``context``, saída bruta do modelo nem mensagens de exceção do SDK.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

LOGGER_NAME = "stride_api"

# Campos extras aceitos. Qualquer outro é descartado pelo formatter.
ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "event",
        "error_code",
        "duration_ms",
        "status_code",
        "method",
        "path",
        "exception_type",
        "error_count",
        "model_calls",
    }
)

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str | None = None) -> Token[str | None]:
    """Define o request_id do contexto atual (gera um se não informado)."""
    return _request_id.set(request_id or new_request_id())


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()


class JsonFormatter(logging.Formatter):
    """Serializa o registro como uma linha JSON usando apenas campos permitidos.

    O texto da mensagem não é emitido (``record.msg`` pode conter dados do
    chamador); use o campo ``event`` com um identificador constante. Mensagem e
    traceback de exceções também são omitidos: só o tipo da exceção sai.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        for name in ALLOWED_FIELDS:
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        if "exception_type" not in payload and record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura o logger da aplicação (idempotente)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, "_stride_handler", False):
            logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._stride_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def log_event(
    event: str,
    *,
    level: int = logging.INFO,
    error_code: str | None = None,
    duration_ms: float | None = None,
    **fields: Any,
) -> None:
    """Registra um evento estruturado. Campos fora da lista permitida são ignorados."""
    extra: dict[str, Any] = {"event": event}
    if error_code is not None:
        extra["error_code"] = error_code
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    extra.update({k: v for k, v in fields.items() if k in ALLOWED_FIELDS and k != "event"})
    get_logger().log(level, event, extra=extra)


class Timer:
    """Cronômetro simples para medir a duração de uma requisição."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
