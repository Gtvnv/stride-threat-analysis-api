"""Testes de propriedade dos esquemas de ameaça."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.schemas.threat import Severity, StrideCategory, Threat

REQUIRED_FIELDS = ["category", "component", "description", "severity", "mitigation"]

_text = st.text(min_size=1, max_size=200).filter(lambda s: s.strip() != "")

valid_threat_dicts = st.fixed_dictionaries(
    {
        "category": st.sampled_from([c.value for c in StrideCategory]),
        "component": _text,
        "description": _text,
        "severity": st.sampled_from([s.value for s in Severity]),
        "mitigation": _text,
    }
)

_whitespace = st.text(alphabet=" \t\n\r", max_size=10)


# Feature: stride-threat-analysis-api, Property 4
# **Validates: Requirements 4.1**
@settings(max_examples=100)
@given(
    data=valid_threat_dicts,
    field=st.sampled_from(REQUIRED_FIELDS),
    mode=st.sampled_from(["missing", "null", "empty", "whitespace"]),
    whitespace=_whitespace,
)
def test_threat_rejects_missing_null_empty_or_blank_required_field(
    data, field, mode, whitespace
):
    Threat.model_validate(data)  # o objeto base é válido

    broken = dict(data)
    if mode == "missing":
        del broken[field]
    elif mode == "null":
        broken[field] = None
    elif mode == "empty":
        broken[field] = ""
    else:
        broken[field] = whitespace

    with pytest.raises(ValidationError):
        Threat.model_validate(broken)


_CATEGORY_VALUES = {c.value for c in StrideCategory}
_SEVERITY_VALUES = {s.value for s in Severity}


def _variants(value):
    """Variantes de caixa e de sublinhado de um valor canônico."""
    return {
        value.lower(),
        value.upper(),
        value.swapcase(),
        value.replace(" ", "_"),
        value.replace(" ", "_").lower(),
    } - {value}


_near_misses = st.sampled_from(
    sorted(
        {v for val in _CATEGORY_VALUES | _SEVERITY_VALUES for v in _variants(val)}
    )
)


def _accepts(field, value):
    data = {
        "category": "Spoofing",
        "component": "c",
        "description": "d",
        "severity": "Low",
        "mitigation": "m",
    }
    data[field] = value
    try:
        Threat.model_validate(data)
    except ValidationError:
        return False
    return True


# Feature: stride-threat-analysis-api, Property 5
# **Validates: Requirements 4.2**
@settings(max_examples=100)
@given(
    value=st.one_of(
        st.text(max_size=40),
        _near_misses,
        st.sampled_from(sorted(_CATEGORY_VALUES | _SEVERITY_VALUES)),
    )
)
def test_category_and_severity_accept_only_exact_case_sensitive_values(value):
    assert _accepts("category", value) == (value in _CATEGORY_VALUES)
    assert _accepts("severity", value) == (value in _SEVERITY_VALUES)


# --- Property 6 -------------------------------------------------------------

from app.schemas.threat import ThreatReport  # noqa: E402

_json_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=200
).filter(lambda s: s.strip() != "")

_text_list = st.lists(_json_text, max_size=5)

valid_report_dicts = st.fixed_dictionaries(
    {
        "components": _text_list,
        "data_flows": _text_list,
        "trust_boundaries": _text_list,
        "summary": _json_text,
        "threats": st.lists(
            st.fixed_dictionaries(
                {
                    "category": st.sampled_from([c.value for c in StrideCategory]),
                    "component": _json_text,
                    "description": _json_text,
                    "severity": st.sampled_from([s.value for s in Severity]),
                    "mitigation": _json_text,
                }
            ),
            max_size=5,
        ),
        "disclaimer": _json_text,
    }
)


# Feature: stride-threat-analysis-api, Property 6
# **Validates: Requirements 4.7**
@settings(max_examples=100)
@given(data=valid_report_dicts)
def test_threat_report_json_round_trip_is_equal(data):
    report = ThreatReport.model_validate(data)
    restored = ThreatReport.model_validate_json(report.model_dump_json())
    assert restored == report


# --- Property 7 -------------------------------------------------------------

_THREAT = {
    "category": "Spoofing",
    "component": "c",
    "description": "d",
    "severity": "Low",
    "mitigation": "m",
}


def _report(**overrides):
    data = {
        "components": [],
        "data_flows": [],
        "trust_boundaries": [],
        "summary": "s",
        "threats": [],
        "disclaimer": "x",
    }
    data.update(overrides)
    return data


def _report_ok(data):
    try:
        ThreatReport.model_validate(data)
    except ValidationError:
        return False
    return True


_list_fields = st.sampled_from(["components", "data_flows", "trust_boundaries"])
_text_chars = st.sampled_from(["a", "é", "日"])


# Feature: stride-threat-analysis-api, Property 7
# **Validates: Requirements 4.5**
@settings(max_examples=100)
@given(count=st.integers(min_value=0, max_value=53))
def test_threats_list_accepts_at_most_50_items(count):
    data = _report(threats=[dict(_THREAT) for _ in range(count)])
    assert _report_ok(data) == (count <= 50)


# Feature: stride-threat-analysis-api, Property 7
# **Validates: Requirements 4.5**
@settings(max_examples=100)
@given(field=_list_fields, count=st.integers(min_value=0, max_value=53))
def test_descriptive_lists_accept_at_most_50_items(field, count):
    data = _report(**{field: ["x"] * count})
    assert _report_ok(data) == (count <= 50)


# Feature: stride-threat-analysis-api, Property 7
# **Validates: Requirements 4.5**
@settings(max_examples=100)
@given(
    target=st.sampled_from(
        ["summary", "component", "description", "mitigation", "list_item"]
    ),
    length=st.sampled_from([1, 1999, 2000, 2001, 2002, 2100]),
    char=_text_chars,
)
def test_text_fields_accept_at_most_2000_characters(target, length, char):
    text = char * length
    if target == "summary":
        data = _report(summary=text)
    elif target == "list_item":
        data = _report(components=[text])
    else:
        data = _report(threats=[{**_THREAT, target: text}])
    assert _report_ok(data) == (length <= 2000)
