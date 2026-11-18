"""Testes unitários do Image_Validator (Requirements 2.2, 2.3)."""

from __future__ import annotations

import pytest

from app.api.errors import AppError
from app.services.image_validator import JPEG_SIGNATURE, PNG_SIGNATURE, validate_image

LIMIT = 100


def _png(size: int) -> bytes:
    return PNG_SIGNATURE + b"a" * (size - len(PNG_SIGNATURE))


def _code(content: bytes, declared: str | None, limit: int = LIMIT) -> str:
    with pytest.raises(AppError) as exc:
        validate_image(content, declared, limit)
    return exc.value.code


def test_size_exactly_at_limit_is_accepted():
    assert validate_image(_png(LIMIT), "image/png", LIMIT) is None
    assert validate_image(JPEG_SIGNATURE + b"a" * (LIMIT - 3), "image/jpeg", LIMIT) is None


def test_size_one_over_limit_is_413():
    assert _code(_png(LIMIT + 1), "image/png") == "file_too_large"


def test_empty_file_is_400():
    assert _code(b"", "image/png") == "file_empty"
    assert _code(b"", "image/jpeg") == "file_empty"


def test_signature_mismatch_is_415():
    assert _code(JPEG_SIGNATURE + b"aaaa", "image/png") == "signature_mismatch"
    assert _code(_png(20), "image/jpeg") == "signature_mismatch"


def test_disallowed_or_missing_type_is_415():
    assert _code(_png(20), "image/gif") == "unsupported_media_type"
    assert _code(_png(20), None) == "unsupported_media_type"


def test_declared_type_ignores_case_and_parameters():
    assert validate_image(_png(20), "IMAGE/PNG; charset=binary", LIMIT) is None
