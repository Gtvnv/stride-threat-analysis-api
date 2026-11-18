"""Testes de propriedade do Image_Validator."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.api.errors import AppError
from app.services.image_validator import JPEG_SIGNATURE, PNG_SIGNATURE, validate_image

SIGNATURES = {"image/png": PNG_SIGNATURE, "image/jpeg": JPEG_SIGNATURE}

declared_types = st.one_of(
    st.none(),
    st.sampled_from(
        [
            "image/png",
            "image/jpeg",
            "IMAGE/PNG",
            "image/jpeg; charset=binary",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "",
        ]
    ),
    st.text(max_size=20),
)

contents = st.one_of(
    st.binary(max_size=64),
    st.binary(max_size=48).map(lambda b: PNG_SIGNATURE + b),
    st.binary(max_size=48).map(lambda b: JPEG_SIGNATURE + b),
)


def _normalize(declared):
    if declared is None:
        return None
    return declared.split(";", 1)[0].strip().lower()


def _expected(content: bytes, declared, max_size: int) -> str | None:
    """Oráculo independente: código de erro esperado ou None se aceita."""
    normalized = _normalize(declared)
    if normalized not in SIGNATURES:
        return "unsupported_media_type"
    if len(content) > max_size:
        return "file_too_large"
    if len(content) == 0:
        return "file_empty"
    if not content.startswith(SIGNATURES[normalized]):
        return "signature_mismatch"
    return None


# Feature: stride-threat-analysis-api, Property 1
# **Validates: Requirements 1.6, 2.1, 2.2, 2.3, 2.5, 2.6**
@settings(max_examples=200)
@given(content=contents, declared=declared_types, max_size=st.integers(1, 80))
def test_image_validator_accepts_iff_rules_hold(content, declared, max_size):
    expected = _expected(content, declared, max_size)
    if expected is None:
        assert validate_image(content, declared, max_size) is None
    else:
        with pytest.raises(AppError) as exc:
            validate_image(content, declared, max_size)
        assert exc.value.code == expected


# Feature: stride-threat-analysis-api, Property 1 (limite: tamanho == max_size é aceito)
# **Validates: Requirements 2.2**
@settings(max_examples=100)
@given(
    declared=st.sampled_from(list(SIGNATURES)),
    tail=st.binary(min_size=1, max_size=32),
)
def test_image_validator_accepts_size_equal_to_max(declared, tail):
    content = SIGNATURES[declared] + tail
    assert validate_image(content, declared, len(content)) is None
    with pytest.raises(AppError) as exc:
        validate_image(content, declared, len(content) - 1)
    assert exc.value.code == "file_too_large"


# --- Property 2: Leitura limitada em memória ---------------------------------

import asyncio  # noqa: E402

from starlette.requests import Request  # noqa: E402

from app.api.upload import read_upload  # noqa: E402

_BOUNDARY = "propboundary"


def _upload_body(data: bytes, content_type: str) -> tuple[bytes, int]:
    """Corpo multipart com a parte 'file'; devolve (corpo, bytes antes dos dados)."""
    prefix = (
        f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode()
    return prefix + data + f"\r\n--{_BOUNDARY}--\r\n".encode(), len(prefix)


def _upload_request(body: bytes, chunk: int, consumed: list[int]) -> Request:
    chunks = [body[i : i + chunk] for i in range(0, len(body), chunk)] or [b""]
    state = {"i": 0}

    async def receive():
        i = state["i"]
        if i >= len(chunks):
            return {"type": "http.disconnect"}
        state["i"] += 1
        consumed.append(len(chunks[i]))
        return {"type": "http.request", "body": chunks[i], "more_body": i < len(chunks) - 1}

    headers = [(b"content-type", f"multipart/form-data; boundary={_BOUNDARY}".encode())]
    scope = {"type": "http", "method": "POST", "headers": headers, "path": "/"}
    return Request(scope, receive)


# Feature: stride-threat-analysis-api, Property 2
# **Validates: Requirements 2.2, 2.7**
@settings(max_examples=150, deadline=None)
@given(
    data=st.binary(min_size=1, max_size=600),
    max_size=st.integers(1, 600),
    chunk=st.integers(1, 200),
    content_type=st.sampled_from(["image/png", "image/jpeg"]),
)
def test_bounded_read_limits_memory_consumption(data, max_size, chunk, content_type):
    body, header_len = _upload_body(data, content_type)
    consumed: list[int] = []
    request = _upload_request(body, chunk, consumed)

    if len(data) <= max_size:
        parsed = asyncio.run(read_upload(request, max_size))
        assert parsed.image is not None
        assert parsed.image.content == data
        assert parsed.image.content_type == content_type
    else:
        with pytest.raises(AppError) as exc:
            asyncio.run(read_upload(request, max_size))
        assert exc.value.code == "file_too_large"
        assert exc.value.status_code == 413
        # no máximo Max_Image_Size + um chunk (mais o cabeçalho da parte) e o
        # lookahead do parser: ele retém bytes que podem ser início do
        # delimitador "\r\n--<boundary>" antes de emitir os dados da parte.
        lookahead = len(f"\r\n--{_BOUNDARY}")
        assert sum(consumed) <= header_len + max_size + chunk + lookahead
