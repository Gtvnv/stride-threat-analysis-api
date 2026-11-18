"""Testes unitários dos esquemas (Requirements 4.1, 4.2, 4.8)."""

import pytest
from pydantic import ValidationError

from app.schemas.threat import (
    HUMAN_REVIEW_NOTICE,
    Severity,
    StrideCategory,
    Threat,
    ThreatAnalysis,
    ThreatReport,
)

GLOSSARY_MAPPING = {
    "Spoofing": ("SPOOFING", "Spoofing"),
    "Tampering": ("TAMPERING", "Tampering"),
    "Repudiation": ("REPUDIATION", "Repudiation"),
    "Information_Disclosure": ("INFORMATION_DISCLOSURE", "Information Disclosure"),
    "Denial_of_Service": ("DENIAL_OF_SERVICE", "Denial of Service"),
    "Elevation_of_Privilege": ("ELEVATION_OF_PRIVILEGE", "Elevation of Privilege"),
}


def _threat(**overrides):
    data = {
        "category": "Spoofing",
        "component": "API",
        "description": "desc",
        "severity": "High",
        "mitigation": "mitigar",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("term,expected", GLOSSARY_MAPPING.items())
def test_glossary_maps_to_enum_member_and_value(term, expected):
    member_name, value = expected
    member = StrideCategory[member_name]
    assert member.value == value
    assert StrideCategory(value) is member
    assert Threat.model_validate(_threat(category=value)).category is member
    # O identificador do glossário com underscore só é aceito onde coincide com o valor.
    if "_" in term:
        with pytest.raises(ValidationError):
            Threat.model_validate(_threat(category=term))


def test_enum_has_exactly_six_categories_and_four_severities():
    assert len(StrideCategory) == 6
    assert [s.value for s in Severity] == ["Low", "Medium", "High", "Critical"]


@pytest.mark.parametrize("bad", ["spoofing", "SPOOFING", "information disclosure", "Information_Disclosure", ""])
def test_category_is_exact_and_case_sensitive(bad):
    with pytest.raises(ValidationError):
        Threat.model_validate(_threat(category=bad))


@pytest.mark.parametrize("bad", ["low", "HIGH", "Urgent"])
def test_severity_is_exact_and_case_sensitive(bad):
    with pytest.raises(ValidationError):
        Threat.model_validate(_threat(severity=bad))


@pytest.mark.parametrize("field", ["category", "component", "description", "severity", "mitigation"])
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_threat_rejects_missing_null_empty_or_blank(field, bad):
    with pytest.raises(ValidationError):
        Threat.model_validate(_threat(**{field: bad}))
    data = _threat()
    del data[field]
    with pytest.raises(ValidationError):
        Threat.model_validate(data)


def test_summary_with_empty_threats_is_valid():
    analysis = ThreatAnalysis.model_validate(
        {
            "components": [],
            "data_flows": [],
            "trust_boundaries": [],
            "summary": "Sem arquitetura identificável no diagrama.",
            "threats": [],
        }
    )
    assert analysis.threats == []
    assert analysis.summary


@pytest.mark.parametrize("summary", ["", "   ", None])
def test_summary_required_even_with_empty_threats(summary):
    with pytest.raises(ValidationError):
        ThreatAnalysis.model_validate(
            {"components": [], "data_flows": [], "trust_boundaries": [], "summary": summary, "threats": []}
        )


def test_report_roundtrip_and_disclaimer():
    report = ThreatReport(
        components=["a"],
        data_flows=["b"],
        trust_boundaries=["c"],
        summary="s",
        threats=[Threat.model_validate(_threat())],
        disclaimer=HUMAN_REVIEW_NOTICE,
    )
    assert ThreatReport.model_validate_json(report.model_dump_json()) == report
