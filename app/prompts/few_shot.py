"""Exemplos few-shot de `Threat` usados no prompt de sistema.

Os valores de `category` e `severity` seguem exatamente os valores do esquema
(`app/schemas/threat.py`). Os textos livres estão em pt-BR.
"""

import json
from typing import Any

FEW_SHOT_THREATS: list[dict[str, Any]] = [
    {
        "category": "Spoofing",
        "component": "API Gateway",
        "description": (
            "O diagrama não mostra autenticação entre o cliente externo e o API "
            "Gateway, o que permite que um atacante se passe por um usuário legítimo."
        ),
        "severity": "High",
        "mitigation": (
            "Exigir autenticação forte (por exemplo OAuth 2.0/OIDC com tokens de "
            "curta duração) e, quando aplicável, autenticação mútua (mTLS)."
        ),
    },
    {
        "category": "Information Disclosure",
        "component": "Banco de dados",
        "description": (
            "O fluxo entre o servidor de aplicação e o banco de dados não indica "
            "criptografia em trânsito, expondo dados sensíveis a interceptação."
        ),
        "severity": "High",
        "mitigation": (
            "Habilitar TLS na conexão com o banco, criptografar dados em repouso e "
            "restringir o acesso por rede privada."
        ),
    },
    {
        "category": "Denial of Service",
        "component": "Balanceador de carga",
        "description": (
            "O balanceador está exposto à internet e o diagrama não mostra limitação "
            "de taxa, o que facilita o esgotamento de recursos por excesso de requisições."
        ),
        "severity": "Medium",
        "mitigation": (
            "Aplicar limitação de taxa, WAF e proteção contra DDoS, além de "
            "dimensionar o serviço para escalar sob carga."
        ),
    },
]


def format_few_shot_examples() -> str:
    """Devolve os exemplos formatados como JSON, um por bloco numerado."""
    blocks = []
    for index, example in enumerate(FEW_SHOT_THREATS, start=1):
        blocks.append(
            f"Exemplo {index}:\n{json.dumps(example, ensure_ascii=False, indent=2)}"
        )
    return "\n\n".join(blocks)
