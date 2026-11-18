"""Validação da saída bruta do modelo contra o esquema do relatório de ameaças.

Em qualquer falha o conteúdo do modelo é descartado: o log recebe só a categoria
e a quantidade de erros (nunca o texto bruto nem o ``input`` dos erros) e o
chamador recebe um ``AppError`` com mensagem constante.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.api.errors import AppError
from app.core.logging import log_event
from app.schemas.threat import HUMAN_REVIEW_NOTICE, ThreatAnalysis, ThreatReport

_EVENT = "model_output_invalid"


def _reject(category: str, error_count: int) -> AppError:
    log_event(
        _EVENT,
        level=logging.WARNING,
        error_code=_EVENT,
        exception_type=category,
        error_count=error_count,
    )
    return AppError("model_output_invalid")


def validate_model_output(raw: str) -> ThreatReport:
    """Parseia e valida a saída do modelo.

    Campos desconhecidos são ignorados pelo esquema e o ``disclaimer`` é sempre
    o aviso da API. Levanta ``AppError("model_output_invalid")`` (502) em
    qualquer falha.
    """
    try:
        analysis = ThreatAnalysis.model_validate_json(raw)
        return ThreatReport(
            **{name: getattr(analysis, name) for name in ThreatAnalysis.model_fields},
            disclaimer=HUMAN_REVIEW_NOTICE,
        )
    except ValidationError as exc:
        # Só a contagem; exc.errors() contém ``input`` com o conteúdo bruto.
        raise _reject("ValidationError", exc.error_count()) from None
    except Exception as exc:  # noqa: BLE001 - qualquer falha vira erro genérico
        raise _reject(type(exc).__name__, 1) from None
