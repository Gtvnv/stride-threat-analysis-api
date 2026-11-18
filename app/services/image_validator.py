"""Validação da imagem enviada: tipo declarado, tamanho e assinatura."""

from __future__ import annotations

from typing import Final

from app.api.errors import AppError

PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE: Final[bytes] = b"\xff\xd8\xff"

ALLOWED_TYPES: Final[dict[str, bytes]] = {
    "image/png": PNG_SIGNATURE,
    "image/jpeg": JPEG_SIGNATURE,
}


def _normalize_type(declared_type: str | None) -> str | None:
    if declared_type is None:
        return None
    return declared_type.split(";", 1)[0].strip().lower()


def validate_image(content: bytes, declared_type: str | None, max_size: int) -> None:
    """Levanta AppError (415, 413, 400 ou 415) na ordem das verificações.

    Retorna None se a imagem é aceita. Tamanho igual a ``max_size`` é aceito.
    """
    normalized = _normalize_type(declared_type)
    if normalized is None or normalized not in ALLOWED_TYPES:
        raise AppError("unsupported_media_type")
    if len(content) > max_size:
        raise AppError("file_too_large")
    if len(content) == 0:
        raise AppError("file_empty")
    if not content.startswith(ALLOWED_TYPES[normalized]):
        raise AppError("signature_mismatch")
