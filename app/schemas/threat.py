"""Esquemas Pydantic do relatório de ameaças STRIDE."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

HUMAN_REVIEW_NOTICE = (
    "Esta análise foi gerada por um modelo de linguagem e pode conter erros ou "
    "omissões. Ela exige revisão humana e deve ser usada apenas de forma ética e "
    "defensiva, em sistemas que você possui ou está autorizado a avaliar."
)

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class StrideCategory(str, Enum):
    SPOOFING = "Spoofing"
    TAMPERING = "Tampering"
    REPUDIATION = "Repudiation"
    INFORMATION_DISCLOSURE = "Information Disclosure"
    DENIAL_OF_SERVICE = "Denial of Service"
    ELEVATION_OF_PRIVILEGE = "Elevation of Privilege"


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Threat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: StrideCategory
    component: NonEmptyText
    description: NonEmptyText
    severity: Severity
    mitigation: NonEmptyText


class ThreatAnalysis(BaseModel):
    """Saída esperada do modelo (sem o disclaimer, que é inserido pela API)."""

    model_config = ConfigDict(extra="ignore")

    components: list[NonEmptyText] = Field(max_length=50)
    data_flows: list[NonEmptyText] = Field(max_length=50)
    trust_boundaries: list[NonEmptyText] = Field(max_length=50)
    summary: NonEmptyText
    threats: list[Threat] = Field(max_length=50)


class ThreatReport(ThreatAnalysis):
    disclaimer: NonEmptyText
