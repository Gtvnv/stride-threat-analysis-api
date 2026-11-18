"""Testes de propriedade do Response_Validator."""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from app.schemas.threat import HUMAN_REVIEW_NOTICE, Severity, StrideCategory, ThreatAnalysis
from app.services.response_validator import validate_model_output

ROOT_FIELDS = {"components", "data_flows", "trust_boundaries", "summary", "threats", "disclaimer"}
THREAT_FIELDS = {"category", "component", "description", "severity", "mitigation"}

_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), max_codepoint=0x2FFF) | st.just(" "),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() != "")
_json_value = st.recursive(
    st.none() | st.booleans() | st.integers(-1000, 1000) | st.text(max_size=30),
    lambda children: st.lists(children, max_size=3)
    | st.dictionaries(st.text(max_size=10), children, max_size=3),
    max_leaves=6,
)


def _extras(reserved: set[str]):
    return st.dictionaries(
        st.text(min_size=1, max_size=15).filter(lambda k: k not in reserved),
        _json_value,
        min_size=1,
        max_size=4,
    )


_threat = st.fixed_dictionaries(
    {
        "category": st.sampled_from([c.value for c in StrideCategory]),
        "component": _text,
        "description": _text,
        "severity": st.sampled_from([s.value for s in Severity]),
        "mitigation": _text,
    }
)

_output = st.fixed_dictionaries(
    {
        "components": st.lists(_text, max_size=5),
        "data_flows": st.lists(_text, max_size=5),
        "trust_boundaries": st.lists(_text, max_size=5),
        "summary": _text,
        "threats": st.lists(_threat, max_size=5),
    }
)


@st.composite
def output_with_extras(draw):
    data = draw(_output)
    data = {**data, **draw(_extras(ROOT_FIELDS))}
    data["threats"] = [{**t, **draw(_extras(THREAT_FIELDS))} for t in data["threats"]]
    return data


# Feature: stride-threat-analysis-api, Property 8
# **Validates: Requirements 4.9**
@settings(max_examples=100)
@given(data=output_with_extras())
def test_unknown_fields_are_discarded_and_defined_fields_keep_values(data):
    report = validate_model_output(json.dumps(data))
    dumped = report.model_dump(mode="json")

    assert set(dumped) == set(ThreatAnalysis.model_fields) | {"disclaimer"}
    for threat in dumped["threats"]:
        assert set(threat) == THREAT_FIELDS

    # Os campos definidos mantêm os valores (texto é aparado pelo esquema).
    for name in ("components", "data_flows", "trust_boundaries"):
        assert dumped[name] == [s.strip() for s in data[name]]
    assert dumped["summary"] == data["summary"].strip()
    assert len(dumped["threats"]) == len(data["threats"])
    for out, src in zip(dumped["threats"], data["threats"]):
        for field in THREAT_FIELDS:
            expected = src[field].strip() if field not in ("category", "severity") else src[field]
            assert out[field] == expected


@st.composite
def output_with_optional_disclaimer(draw):
    data = draw(_output)
    if draw(st.booleans()):
        data = {**data, "disclaimer": draw(_json_value)}
    return data


# Feature: stride-threat-analysis-api, Property 9
# **Validates: Requirements 4.6**
@settings(max_examples=100)
@given(data=output_with_optional_disclaimer())
def test_disclaimer_is_always_the_api_notice(data):
    report = validate_model_output(json.dumps(data))

    assert report.disclaimer == HUMAN_REVIEW_NOTICE
    assert report.model_dump(mode="json")["disclaimer"] == HUMAN_REVIEW_NOTICE


# --- Property 10 -----------------------------------------------------------

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_marker = st.text(alphabet="0123456789abcdef", min_size=16, max_size=32).map(
    lambda s: f"LEAK-{s}-MARK"
)


@st.composite
def invalid_output_with_marker(draw):
    """Saída inválida do modelo que embute um marcador único. Retorna (marcador, texto)."""
    marker = draw(_marker)
    prefix = draw(st.text(alphabet="abc xyz", max_size=10))
    kind = draw(
        st.sampled_from(
            ["not_json", "json_array", "json_scalar", "missing_fields", "bad_category",
             "bad_severity", "wrong_type", "truncated"]
        )
    )
    valid = {
        "components": ["api"],
        "data_flows": ["a -> b"],
        "trust_boundaries": [],
        "summary": "resumo",
        "threats": [],
    }
    threat = {
        "category": "Spoofing",
        "component": "api",
        "description": "d",
        "severity": "High",
        "mitigation": "m",
    }
    if kind == "not_json":
        text = f"{prefix} {marker} nao e json"
    elif kind == "json_array":
        text = json.dumps([marker, prefix])
    elif kind == "json_scalar":
        text = json.dumps(marker)
    elif kind == "missing_fields":
        text = json.dumps({"summary": marker})
    elif kind == "bad_category":
        text = json.dumps({**valid, "threats": [{**threat, "category": marker}]})
    elif kind == "bad_severity":
        text = json.dumps({**valid, "threats": [{**threat, "severity": marker}]})
    elif kind == "wrong_type":
        text = json.dumps({**valid, "components": marker, "threats": marker})
    else:
        text = json.dumps({**valid, "summary": marker})[:-1]
    return marker, text


# Feature: stride-threat-analysis-api, Property 10
# **Validates: Requirements 3.7, 4.4**
@settings(max_examples=100, deadline=None)
@given(case=invalid_output_with_marker())
def test_invalid_model_output_never_leaks_and_does_not_retry(case):
    import os
    from unittest import mock

    from fastapi.testclient import TestClient

    from app.clients.azure_openai_client import get_model_client
    from app.main import create_app
    from tests.conftest import FakeModelClient, assert_error_response

    marker, raw = case
    env = {
        "AZURE_OPENAI_ENDPOINT": "https://fake.example.invalid",
        "AZURE_OPENAI_API_KEY": "fake-key",
        "AZURE_OPENAI_DEPLOYMENT": "fake-deployment",
        "AZURE_OPENAI_API_VERSION": "2024-01-01",
    }
    fake = FakeModelClient(response=raw)
    app = create_app()
    app.dependency_overrides[get_model_client] = lambda: fake
    with mock.patch.dict(os.environ, env):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/analyze", files={"file": ("d.png", _PNG, "image/png")}
        )

    assert_error_response(response, 502, "model_output_invalid", forbidden=(marker,))
    assert "threats" not in response.json()
    assert fake.call_count == 1
