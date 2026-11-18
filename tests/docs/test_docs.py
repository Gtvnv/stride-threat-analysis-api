"""Testes de fumaça da documentação (README, links, exemplos e varredura de segredos)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.schemas.threat import ThreatReport

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

REQUIRED_SECTIONS = [
    "Objetivo",
    "Arquitetura",
    "Metodologia STRIDE",
    "Pré-requisitos",
    "Configuração do Azure OpenAI",
    "Instalação",
    "Execução",
    "Exemplos de requisição e resposta",
    "Técnicas de engenharia de prompt",
    "Estrutura do projeto",
    "Limitações",
]
WARNING_SECTION = "Aviso de revisão humana e uso ético e defensivo"

IGNORED_DIRS = {".git", ".venv", "__pycache__", ".hypothesis", ".pytest_cache"}
IGNORED_FILES = {".env"}

AZURE_ENDPOINT = re.compile(r"https://([A-Za-z0-9_.<>*-]+)\.openai\.azure\.com", re.IGNORECASE)
HEX_KEY = re.compile(r"(?<![0-9A-Fa-f])[0-9a-f]{32}(?![0-9A-Fa-f])")
API_KEY_VALUE = re.compile(r"api-key\s*[:=]\s*[\"']?([A-Za-z0-9_\-]{20,})", re.IGNORECASE)
SK_KEY = re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _headings(text: str) -> set[str]:
    return {m.group(1).strip() for m in re.finditer(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)}


def test_readme_has_eleven_sections_and_warning_section() -> None:
    headings = _headings(_readme())
    missing = [s for s in REQUIRED_SECTIONS if s not in headings]
    assert not missing, f"Seções ausentes no README: {missing}"
    assert len(REQUIRED_SECTIONS) == 11
    assert WARNING_SECTION in headings


def test_readme_relative_links_resolve() -> None:
    text = _readme()
    targets = re.findall(r"!?\[[^\]]*\]\(([^)\s]+)\)", text)
    relative = [
        t.split("#", 1)[0]
        for t in targets
        if not re.match(r"^[a-z][a-z0-9+.-]*:", t, re.IGNORECASE) and not t.startswith("#")
    ]
    assert any(t.startswith("docs/") for t in relative)
    assert any(t.startswith("examples/") for t in relative)
    broken = [t for t in relative if t and not (ROOT / t).exists()]
    assert not broken, f"Links relativos quebrados: {broken}"


def test_example_image_and_license_exist() -> None:
    image = ROOT / "images" / "exemplo-arquitetura.png"
    assert image.is_file() and image.stat().st_size > 0
    assert "images/exemplo-arquitetura.png" in _readme()
    license_file = ROOT / "LICENSE"
    assert license_file.is_file()
    assert "MIT" in license_file.read_text(encoding="utf-8")


def test_readme_clone_url_matches_published_repository() -> None:
    text = _readme()
    assert "https://github.com/Gtvnv/stride-threat-analysis-api.git" in text
    assert "cd stride-threat-analysis-api" in text


def test_example_response_validates_against_threat_report() -> None:
    data = json.loads((ROOT / "examples" / "resposta-exemplo.json").read_text(encoding="utf-8"))
    report = ThreatReport.model_validate(data)
    assert report.disclaimer


def _repo_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts
        if any(part in IGNORED_DIRS for part in rel_parts[:-1]):
            continue
        if path.name in IGNORED_FILES:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def _is_placeholder_host(host: str) -> bool:
    lowered = host.lower()
    return (
        "<" in host
        or ">" in host
        or "*" in host
        or lowered in {"fake", "example", "x", "seu-recurso", "your-resource", "meu-recurso"}
        or lowered.startswith("secret-endpoint-")  # hosts fictícios dos testes
        or lowered.startswith(("fake", "example", "seu-", "your-", "meu-"))
        or "example.invalid" in lowered
        or lowered.endswith(".invalid")
    )


def test_repository_has_no_real_endpoints_or_keys() -> None:
    findings: list[str] = []
    for path, text in _repo_text_files():
        rel = path.relative_to(ROOT).as_posix()
        for m in AZURE_ENDPOINT.finditer(text):
            if not _is_placeholder_host(m.group(1)):
                findings.append(f"{rel}: endpoint {m.group(0)}")
        for m in HEX_KEY.finditer(text):
            findings.append(f"{rel}: chave hex de 32 caracteres")
        for m in API_KEY_VALUE.finditer(text):
            value = m.group(1)
            if not value.lower().startswith(("fake", "test", "your", "seu", "example")):
                findings.append(f"{rel}: api-key com valor longo")
        for m in SK_KEY.finditer(text):
            findings.append(f"{rel}: chave sk-")
    assert not findings, "Possíveis segredos/endpoints reais: " + "; ".join(sorted(set(findings)))


@pytest.mark.parametrize("name", [".env"])
def test_scan_ignores_dotenv(name: str) -> None:
    assert name in IGNORED_FILES
