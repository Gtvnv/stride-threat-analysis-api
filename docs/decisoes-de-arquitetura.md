# Decisões de arquitetura

Este documento registra as decisões de design da STRIDE Threat Analysis API e o motivo de cada uma. A API é escrita em Python 3.12 com FastAPI e recebe a imagem de um diagrama de arquitetura (PNG ou JPEG) em `POST /api/v1/analyze`. Ela chama um deployment com visão no Azure OpenAI e devolve um relatório de ameaças STRIDE validado por um esquema Pydantic.

## Visão geral das camadas

As dependências apontam para dentro: `api` depende de `services`, que dependem da interface `ModelClient`, implementada em `clients`. Prompts (`app/prompts`) e esquemas (`app/schemas`) não dependem de HTTP nem de Azure.

```
app/
  main.py          # create_app(), handlers de erro, middleware de log de requisições
  api/             # routes.py, upload.py, errors.py
  core/            # settings.py, logging.py
  services/        # analysis_service.py, image_validator.py, response_validator.py
  prompts/         # system_prompt.py, few_shot.py, prompt_builder.py
  clients/         # model_client.py (Protocol), azure_openai_client.py
  schemas/         # threat.py
```

Ordem das verificações em uma análise (cada falha interrompe o fluxo sem chamar o Azure):

1. `Settings.ensure_ready()`, com 503 se a configuração estiver ausente ou inválida.
2. Leitura do upload em streaming: 400 (sem parte `file` ou corpo não multipart), 415 (tipo declarado não permitido), 413 (limite excedido) e 422 (`context` acima de 2000 caracteres).
3. Arquivo vazio (400) e assinatura divergente do tipo declarado (415), no `Image_Validator`.
4. Montagem do prompt e uma única chamada ao modelo, com 502 em erro do serviço e 504 em timeout.
5. Validação da resposta contra o esquema (502 se inválida) e inclusão do `disclaimer`.

## D1. Formato dos valores de `StrideCategory`

**Decisão.** O valor serializado em JSON é o nome de exibição com espaços. Os membros do enum Python usam underscore.

| Glossário | Membro do enum | Valor no JSON |
|-----------|----------------|---------------|
| Spoofing | `SPOOFING` | `"Spoofing"` |
| Tampering | `TAMPERING` | `"Tampering"` |
| Repudiation | `REPUDIATION` | `"Repudiation"` |
| Information_Disclosure | `INFORMATION_DISCLOSURE` | `"Information Disclosure"` |
| Denial_of_Service | `DENIAL_OF_SERVICE` | `"Denial of Service"` |
| Elevation_of_Privilege | `ELEVATION_OF_PRIVILEGE` | `"Elevation of Privilege"` |

**Alternativa descartada.** Valores com underscore.

**Justificativa.** É a mesma forma que o prompt ensina ao modelo e que o relatório mostra ao leitor. Um único valor evita uma camada de tradução e rejeições espúrias. A comparação é exata e sensível a maiúsculas: `"information disclosure"` e `"Information_Disclosure"` são rejeitados. `Severity` segue a mesma regra (`Low`, `Medium`, `High`, `Critical`).

## D2. Leitura do upload em streaming, sem `UploadFile`

**Decisão.** `app/api/upload.py` usa o parser de baixo nível `python-multipart` (`MultipartParser`) sobre `request.stream()`.

**Alternativa descartada.** `UploadFile` do FastAPI/Starlette.

**Justificativa.** O Starlette consome o corpo inteiro antes de chamar o handler e usa `SpooledTemporaryFile`, que grava em disco quando o arquivo passa de 1 MiB. Isso quebra duas garantias: parar de ler ao exceder o limite e nunca gravar a imagem em disco. Com o leitor próprio:

- A parte `file` acumula em um `bytearray` e levanta 413 assim que passa de `Max_Image_Size`, de modo que a memória fica limitada ao limite mais um chunk.
- O tipo declarado é verificado ao fim dos cabeçalhos da parte, antes de ler o corpo do arquivo (415).
- Nenhum arquivo temporário é criado.
- Como a rota lê o corpo manualmente, ela descreve o formulário em `openapi_extra` para que `/docs` mostre o campo de arquivo e o campo `context`.
- Corpo multipart malformado vira `file_missing` (400).

## D3. `Settings` lida do ambiente a cada análise

**Decisão.** `Settings.from_env()` roda a cada requisição de análise e `ensure_ready()` valida o resultado. É um dataclass imutável, sem valores padrão para endpoint, chave e deployment.

**Alternativa descartada.** Falhar na inicialização.

**Justificativa.** A API deve continuar servindo `/health` e `/docs` mesmo com configuração incompleta, e responder 503 (`service_not_configured`) apenas quando uma análise é pedida. `MAX_IMAGE_SIZE_BYTES` só aceita inteiros decimais entre 1 e 20.971.520. Quando ausente, vale o padrão de 5 MiB. O campo `api_key` tem `repr=False`.

Consequência: com configuração inválida, até uma imagem inválida recebe 503, porque o limite de tamanho faz parte da configuração.

## D4. Cliente Azure sem retentativas e com timeout duplo

**Decisão.** `AzureOpenAIClient` usa `AsyncAzureOpenAI` com `max_retries=0` e `timeout=60`, e envolve a chamada em `asyncio.timeout(60)`. Parâmetros fixos: `temperature=0.1`, `max_tokens=4096`, `response_format={"type": "json_object"}`.

**Alternativa descartada.** Retentativas automáticas do SDK.

**Justificativa.** A saída inválida do modelo não pode gerar nova chamada, e retentativas estourariam o teto de 60 s. Mapeamento de erros:

- Timeout: `ModelTimeoutError`, que vira 504 (`upstream_timeout`).
- Qualquer outra exceção do SDK: `ModelServiceError`, que vira 502 (`upstream_error`). A mensagem original é descartada e não é encadeada.
- `finish_reason` diferente de `stop`, recusa do modelo ou conteúdo vazio: `ModelOutputInvalidError`, que vira 502 (`model_output_invalid`).

O parâmetro `model` recebe o nome do deployment.

## D5. Limite do corpo da requisição

**Decisão.** O corpo total é limitado a `Max_Image_Size` + 64 KiB de sobrecarga multipart, com 413 ao exceder.

**Alternativa descartada.** Sem limite de corpo.

**Justificativa.** Mantém a memória limitada mesmo se o cliente enviar partes extras. A parte `context` tem limite próprio de 8000 bytes (4 bytes por caractere UTF-8 vezes 2000) e de 2000 caracteres decodificados. UTF-8 inválido gera 422 (`invalid_request`).

## D6. Esquema em duas classes

**Decisão.** `ThreatAnalysis` é o que o modelo produz, e `ThreatReport(ThreatAnalysis)` acrescenta `disclaimer`.

**Alternativa descartada.** Um único esquema.

**Justificativa.** A saída do modelo é validada com `extra="ignore"`, o que descarta campos desconhecidos e qualquer `disclaimer` enviado pelo modelo. O `Response_Validator` monta o `ThreatReport` com `disclaimer=HUMAN_REVIEW_NOTICE`, então o aviso vem sempre da API. Limites: 50 ameaças, 50 itens por lista descritiva e 2000 caracteres por texto. Campos de texto passam por `strip_whitespace`, e texto vazio ou só com espaços é rejeitado.

## D7. Idioma da saída

**Decisão.** O prompt pede que os textos livres (`components`, `data_flows`, `trust_boundaries`, `summary`, `component`, `description`, `mitigation`) sejam escritos em pt-BR. Os valores de `category` e `severity` ficam em inglês.

**Alternativa descartada.** Textos em inglês.

**Justificativa.** Alinha a saída com a documentação em pt-BR sem alterar o contrato das enumerações.

## Tratamento uniforme de erros

Todo erro esperado é um `AppError` com código, status e mensagem constantes, definidos em `ERROR_CATALOG`. O corpo é sempre `{"error": {"code": "...", "message": "..."}}`.

| Código | HTTP |
|--------|------|
| `file_missing` | 400 |
| `file_empty` | 400 |
| `file_too_large` | 413 |
| `unsupported_media_type` | 415 |
| `signature_mismatch` | 415 |
| `context_too_long` | 422 |
| `invalid_request` | 422 |
| `service_not_configured` | 503 |
| `upstream_error` | 502 |
| `model_output_invalid` | 502 |
| `upstream_timeout` | 504 |
| `internal_error` | 500 |

O código `invalid_request` (422) foi acrescentado na implementação. Ele cobre erros de validação do FastAPI (`RequestValidationError`) e `context` com UTF-8 inválido, sem repetir o valor enviado. Um handler genérico transforma exceções inesperadas em `internal_error` (500) com mensagem fixa.

## Log estruturado e middleware de requisições

`app/core/logging.py` emite uma linha JSON por evento e só aceita campos de uma lista permitida: `event`, `error_code`, `duration_ms`, `status_code`, `method`, `path`, `exception_type`, `error_count` e `model_calls`, além de `request_id` e `timestamp`. O texto da mensagem e o traceback não são emitidos, e de uma exceção sai apenas o tipo.

Em `app/main.py`, o middleware `request_logging` gera um `request_id` por requisição (via `ContextVar`) e mede a duração. Ele registra `request_completed` com status, método e caminho, ou `request_failed` com o tipo da exceção, e restaura o contexto ao final.

## Testabilidade

`ModelClient` é um `Protocol`. Os testes injetam um fake com `app.dependency_overrides` e não usam credenciais reais. O `conftest.py` bloqueia a rede com `pytest-socket` (no Windows, permite apenas loopback para o event loop), remove as variáveis do Azure e substitui o `__init__` do `AzureOpenAIClient` por uma função que falha com "acesso real ao Azure proibido nos testes". Os testes de propriedade rodam com ao menos 100 exemplos (Hypothesis).

Como a rota chama `Settings.from_env().ensure_ready()` diretamente, os testes de API que trocam o cliente por um fake também definem variáveis de ambiente falsas com `monkeypatch`. Sem isso a rota responde 503.
