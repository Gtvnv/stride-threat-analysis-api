"""Leitor de upload multipart em streaming.

Lê o corpo com ``python_multipart.MultipartParser`` sobre ``request.stream()``.
Não usa ``UploadFile`` nem arquivos temporários: os bytes da imagem existem
somente em memória e a leitura é interrompida ao exceder o limite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from fastapi import Request
from python_multipart.multipart import MultipartParser, parse_options_header

from app.api.errors import AppError

CHUNK_SIZE: Final[int] = 64 * 1024
BODY_OVERHEAD: Final[int] = 64 * 1024
MAX_CONTEXT_CHARS: Final[int] = 2000
# Em UTF-8 um caractere ocupa no máximo 4 bytes.
MAX_CONTEXT_BYTES: Final[int] = MAX_CONTEXT_CHARS * 4
ALLOWED_IMAGE_TYPES: Final[frozenset[str]] = frozenset({"image/png", "image/jpeg"})


@dataclass(frozen=True)
class UploadedImage:
    content: bytes  # somente em memória
    content_type: str | None


@dataclass(frozen=True)
class ParsedRequest:
    image: UploadedImage | None  # None se não houver parte "file"
    context: str | None


def _normalize_type(value: str | None) -> str | None:
    if value is None:
        return None
    return value.split(";", 1)[0].strip().lower()


class _PartCollector:
    """Recebe os callbacks do parser e acumula as partes 'file' e 'context'."""

    def __init__(self, max_image_size: int) -> None:
        self.max_image_size = max_image_size
        self.file_buffer: bytearray | None = None
        self.file_type: str | None = None
        self.context_buffer = bytearray()
        self.has_context = False
        self._reset_part()

    def _reset_part(self) -> None:
        self._headers: dict[str, str] = {}
        self._field = bytearray()
        self._value = bytearray()
        self._target: str | None = None  # "file", "context" ou None (ignorada)

    # callbacks do parser
    def on_part_begin(self) -> None:
        self._reset_part()

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._field += data[start:end]

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._value += data[start:end]

    def on_header_end(self) -> None:
        name = bytes(self._field).decode("latin-1").strip().lower()
        self._headers[name] = bytes(self._value).decode("utf-8", "replace")
        self._field = bytearray()
        self._value = bytearray()

    def on_headers_finished(self) -> None:
        disposition = self._headers.get("content-disposition", "")
        _, params = parse_options_header(disposition)
        raw_name = params.get(b"name")
        name = raw_name.decode("utf-8", "replace") if raw_name else None
        if name == "file" and self.file_buffer is None:
            declared = _normalize_type(self._headers.get("content-type"))
            # 415 antes de ler o corpo do arquivo.
            if declared not in ALLOWED_IMAGE_TYPES:
                raise AppError("unsupported_media_type")
            self.file_type = declared
            self.file_buffer = bytearray()
            self._target = "file"
        elif name == "context" and not self.has_context:
            self.has_context = True
            self._target = "context"

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._target == "file":
            assert self.file_buffer is not None
            self.file_buffer += data[start:end]
            if len(self.file_buffer) > self.max_image_size:
                raise AppError("file_too_large")
        elif self._target == "context":
            self.context_buffer += data[start:end]
            if len(self.context_buffer) > MAX_CONTEXT_BYTES:
                raise AppError("context_too_long")

    def on_part_end(self) -> None:
        self._target = None


def _boundary(request: Request) -> bytes:
    content_type = request.headers.get("content-type")
    if not content_type:
        raise AppError("file_missing")
    value, params = parse_options_header(content_type)
    if value.lower() != b"multipart/form-data":
        raise AppError("file_missing")
    boundary = params.get(b"boundary")
    if not boundary:
        raise AppError("file_missing")
    return boundary


def _decode_context(collector: _PartCollector) -> str | None:
    if not collector.has_context:
        return None
    try:
        text = bytes(collector.context_buffer).decode("utf-8")
    except UnicodeDecodeError:
        raise AppError("invalid_request") from None
    if len(text) > MAX_CONTEXT_CHARS:
        raise AppError("context_too_long")
    return text if text else None


async def read_upload(request: Request, max_image_size: int) -> ParsedRequest:
    """Lê as partes ``file`` e ``context`` do corpo multipart em streaming.

    Levanta AppError: 400 (não multipart / sem ``file``), 413 (imagem ou corpo
    acima do limite), 415 (content type declarado não permitido) e 422
    (``context`` acima de 2000 caracteres ou UTF-8 inválido).
    """
    boundary = _boundary(request)
    max_body = max_image_size + BODY_OVERHEAD
    collector = _PartCollector(max_image_size)
    parser = MultipartParser(
        boundary,
        callbacks={
            "on_part_begin": collector.on_part_begin,
            "on_header_field": collector.on_header_field,
            "on_header_value": collector.on_header_value,
            "on_header_end": collector.on_header_end,
            "on_headers_finished": collector.on_headers_finished,
            "on_part_data": collector.on_part_data,
            "on_part_end": collector.on_part_end,
        },
    )

    total = 0
    try:
        async for chunk in request.stream():
            if not chunk:
                continue
            total += len(chunk)
            if total > max_body:
                raise AppError("file_too_large")
            parser.write(chunk)
        parser.finalize()
    except AppError:
        raise
    except Exception:
        # Corpo multipart malformado.
        raise AppError("file_missing") from None

    context = _decode_context(collector)
    image = None
    if collector.file_buffer is not None:
        image = UploadedImage(bytes(collector.file_buffer), collector.file_type)
    return ParsedRequest(image=image, context=context)
