"""Testes de fumaça da configuração do repositório (.env.example, .gitignore, ci.yml)."""

from __future__ import annotations

import re
from pathlib import Path

from app.core import settings as settings_module

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_GITIGNORE = [
    ".env",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".hypothesis/",
    ".mypy_cache/",
    ".ruff_cache/",
    "uploads/",
    "output/",
    "generated/",
]


def _settings_env_vars() -> set[str]:
    return {
        value
        for name, value in vars(settings_module).items()
        if name.startswith("ENV_") and isinstance(value, str)
    }


def _env_example_vars() -> set[str]:
    names: set[str] = set()
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line.split("=", 1)[0].strip())
    return names


def test_env_example_lists_same_variables_as_settings() -> None:
    """Requirements: 5.2"""
    expected = _settings_env_vars()
    assert expected, "Settings não expõe nenhuma variável ENV_*"
    assert _env_example_vars() == expected


def test_env_example_has_only_placeholders() -> None:
    """Requirements: 5.2"""
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        name, value = line.split("=", 1)
        if name.strip() == "MAX_IMAGE_SIZE_BYTES":
            assert value.strip().isdigit()
        else:
            assert re.fullmatch(r"<[^<>]+>", value.strip()), name


def test_gitignore_contains_required_entries() -> None:
    """Requirements: 5.3"""
    entries = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    missing = [e for e in REQUIRED_GITIGNORE if e not in entries]
    assert not missing, f"Entradas ausentes no .gitignore: {missing}"


def _ci_text() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_ci_triggers_pull_request_and_push_ignoring_main() -> None:
    """Requirements: 6.6, 6.7"""
    text = _ci_text()
    on_block = re.search(r"^on:\s*\n((?:[ \t]+.*\n|\s*\n)+)", text, re.MULTILINE)
    assert on_block, "bloco 'on:' não encontrado"
    block = on_block.group(1)
    assert re.search(r"^\s+pull_request:", block, re.MULTILINE)
    assert re.search(r"^\s+push:", block, re.MULTILINE)
    assert re.search(r"branches-ignore:\s*\n\s*-\s*['\"]?main['\"]?\s*$", block, re.MULTILINE)
    assert "branches:" not in block.replace("branches-ignore:", "")


def test_ci_runs_pytest() -> None:
    """Requirements: 6.6"""
    assert re.search(r"^\s*run:\s*pytest\s*$", _ci_text(), re.MULTILINE)


def test_ci_does_not_reference_azure_secrets() -> None:
    """Requirements: 6.7"""
    text = _ci_text()
    assert "AZURE" not in text.upper()
    assert "secrets." not in text
