"""Testes do leitor de upload em streaming (Requirements 1.4, 2.1, 2.2, 2.4, 2.7, 2.8)."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.errors import AppError
from app.api.upload import CHUNK_SIZE, read_upload

BOUNDARY = "testboundary"


def _part(name: str, data: bytes, content_type: str | None = None) -> bytes:
    disp = f'Content-Disposition: form-data; name="{name}"'
    if content_type:
        disp = f'{disp}; filename="x"\r\nContent-Type: {content_type}'
    return f"--{BOUNDARY}\r\n{disp}\r\n\r\n".encode() + data + b"\r\n"


def _body(*parts: bytes) -> bytes:
    return b"".join(parts) + f"--{BOUNDARY}--\r\n".encode()


def _request(
    body: bytes,
    content_type: str | None = f"multipart/form-data; boundary={BOUNDARY}",
    chunk: int = 1000,
    consumed: list[int] | None = None,
) -> Request:
    chunks = [body[i : i + chunk] for i in range(0, len(body), chunk)] or [b""]
    state = {"i": 0}

    async def receive():
        i = state["i"]
        if i >= len(chunks):
            return {"type": "http.disconnect"}
        state["i"] += 1
        if consumed is not None:
            consumed.append(len(chunks[i]))
        return {"type": "http.request", "body": chunks[i], "more_body": i < len(chunks) - 1}

    headers = []
    if content_type is not None:
        headers.append((b"content-type", content_type.encode()))
    scope = {"type": "http", "method": "POST", "headers": headers, "path": "/"}
    return Request(scope, receive)


async def _code(coro) -> str:
    with pytest.raises(AppError) as exc:
        await coro
    return exc.value.code


async def test_reads_file_and_context():
    data = bytes(range(256)) * 20
    body = _body(_part("file", data, "image/png"), _part("context", "olá".encode()))
    parsed = await read_upload(_request(body), 10_000)
    assert parsed.image is not None
    assert parsed.image.content == data
    assert parsed.image.content_type == "image/png"
    assert parsed.context == "olá"


async def test_file_exactly_at_limit_is_accepted():
    body = _body(_part("file", b"a" * 100, "image/jpeg"))
    parsed = await read_upload(_request(body), 100)
    assert parsed.image is not None and len(parsed.image.content) == 100


async def test_file_over_limit_stops_reading_early():
    consumed: list[int] = []
    body = _body(_part("file", b"a" * 50_000, "image/png"))
    code = await _code(read_upload(_request(body, chunk=1000, consumed=consumed), 5_000))
    assert code == "file_too_large"
    assert sum(consumed) <= 5_000 + 1000 + 1000 + 200  # limite + chunk + cabeçalho da parte
    assert sum(consumed) < len(body)


async def test_total_body_limit():
    body = _body(_part("file", b"a" * 10, "image/png"), _part("extra", b"b" * (CHUNK_SIZE + 10)))
    assert await _code(read_upload(_request(body), 100)) == "file_too_large"


async def test_disallowed_declared_type_is_415():
    body = _body(_part("file", b"abc", "text/plain"))
    assert await _code(read_upload(_request(body), 100)) == "unsupported_media_type"


async def test_missing_declared_type_is_415():
    body = _body(_part("file", b"abc"))
    assert await _code(read_upload(_request(body), 100)) == "unsupported_media_type"


async def test_missing_file_part_returns_none_image():
    parsed = await read_upload(_request(_body(_part("context", b"x"))), 100)
    assert parsed.image is None and parsed.context == "x"


async def test_non_multipart_is_400():
    req = _request(b"{}", content_type="application/json")
    assert await _code(read_upload(req, 100)) == "file_missing"
    assert await _code(read_upload(_request(b"", content_type=None), 100)) == "file_missing"


async def test_context_limits():
    ok = _body(_part("file", b"a", "image/png"), _part("context", "é".encode() * 2000))
    assert (await read_upload(_request(ok), 100)).context == "é" * 2000
    long = _body(_part("file", b"a", "image/png"), _part("context", b"a" * 2001))
    assert await _code(read_upload(_request(long), 100)) == "context_too_long"
    huge = _body(_part("file", b"a", "image/png"), _part("context", b"a" * 9000))
    assert await _code(read_upload(_request(huge), 100_000)) == "context_too_long"


async def test_invalid_utf8_context_is_422():
    body = _body(_part("file", b"a", "image/png"), _part("context", b"\xff\xfe"))
    with pytest.raises(AppError) as exc:
        await read_upload(_request(body), 100)
    assert exc.value.status_code == 422


async def test_empty_file_part_is_read_as_empty_bytes():
    body = _body(_part("file", b"", "image/png"))
    parsed = await read_upload(_request(body), 100)
    assert parsed.image is not None and parsed.image.content == b""


async def test_upload_above_1_mib_never_touches_tempfile(monkeypatch):
    import tempfile

    def _forbidden(*args, **kwargs):
        raise AssertionError("tempfile não pode ser usado no upload")

    for name in (
        "SpooledTemporaryFile",
        "TemporaryFile",
        "NamedTemporaryFile",
        "TemporaryDirectory",
        "mkstemp",
        "mkdtemp",
    ):
        monkeypatch.setattr(tempfile, name, _forbidden)

    size = 1024 * 1024 + 4096
    data = b"\x89PNG\r\n\x1a\n" + b"a" * (size - 8)
    body = _body(_part("file", data, "image/png"), _part("context", b"ctx"))
    parsed = await read_upload(_request(body, chunk=64 * 1024), 2 * 1024 * 1024)
    assert parsed.image is not None
    assert parsed.image.content == data
    assert parsed.context == "ctx"

    too_big = _body(_part("file", b"a" * (size + 10), "image/png"))
    assert await _code(read_upload(_request(too_big, chunk=64 * 1024), size)) == "file_too_large"
