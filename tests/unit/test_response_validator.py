from __future__ import annotations

import json

import pytest

from app.api.errors import AppError
from app.schemas.threat import HUMAN_REVIEW_NOTICE, ThreatReport
from app.services.response_validator import validate_model_output

MARKER = "SEGREDO-MARKER-12345"


def _threat() -> dict:
    return {
        "category": "Information Disclosure",
        "component": "Banco de dados",
        "description": "Sem TLS no fluxo.",
        "severity": "High",
        "mitigation": "Habilitar TLS.",
    }


def _analysis(**overrides) -> dict:
    data = {
        "components": ["API", "Banco"],
        "data_flows": ["API -> Banco"],
        "trust_boundaries": ["Internet / rede interna"],
        "summary": "Arquitetura simples.",
        "threats": [_threat()],
    }
    data.update(overrides)
    return data


def _assert_rejected(raw: str) -> None:
    with pytest.raises(AppError) as exc_info:
        validate_model_output(raw)
    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "model_output_invalid"
    assert MARKER not in exc_info.value.message
    assert MARKER not in str(exc_info.value)


def test_valid_output_returns_report_with_disclaimer() -> None:
    report = validate_model_output(json.dumps(_analysis()))
    assert isinstance(report, ThreatReport)
    assert report.disclaimer == HUMAN_REVIEW_NOTICE
    assert len(report.threats) == 1


@pytest.mark.parametrize("raw", ["", "não é json " + MARKER, '{"components": [', "[]", "null"])
def test_invalid_json_is_rejected_without_leaking(raw: str) -> None:
    _assert_rejected(raw)


def test_schema_violation_invalid_category_is_rejected() -> None:
    threat = _threat() | {"category": "Information_Disclosure", "description": MARKER}
    _assert_rejected(json.dumps(_analysis(threats=[threat])))


def test_schema_violation_missing_field_is_rejected() -> None:
    data = _analysis()
    del data["summary"]
    _assert_rejected(json.dumps(data))


def test_schema_violation_too_many_threats_is_rejected() -> None:
    _assert_rejected(json.dumps(_analysis(threats=[_threat()] * 51)))


def test_diagram_without_architecture_returns_empty_threats_with_summary() -> None:
    summary = "A imagem não contém arquitetura identificável."
    report = validate_model_output(json.dumps(_analysis(threats=[], summary=summary)))
    assert report.threats == []
    assert report.summary == summary


def test_empty_threats_without_summary_is_rejected() -> None:
    _assert_rejected(json.dumps(_analysis(threats=[], summary="  ")))


def test_unknown_fields_and_model_disclaimer_are_discarded() -> None:
    data = _analysis(extra_root="x", disclaimer="falso")
    data["threats"][0]["extra_threat"] = "y"
    report = validate_model_output(json.dumps(data))
    assert report.disclaimer == HUMAN_REVIEW_NOTICE
    dumped = report.model_dump()
    assert "extra_root" not in dumped
    assert "extra_threat" not in dumped["threats"][0]
