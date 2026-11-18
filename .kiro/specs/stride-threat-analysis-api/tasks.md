# Implementation Plan: STRIDE Threat Analysis API

## Overview

Implementação em Python 3.12 e FastAPI, seguindo as camadas do design (`schemas`, `core`, `prompts`, `clients`, `services`, `api`). A ordem é: estrutura do projeto, esquemas, erros e configuração, validação de imagem e leitor de upload, prompts, cliente do modelo, validação da resposta, serviço de análise, rotas, testes, CI, documentação e publicação no Git. Cada etapa termina ligada à anterior, sem código solto.

Linguagem de implementação: Python 3.12 (definida no design). Testes com `pytest`, `pytest-asyncio`, `httpx`, `hypothesis` e `pytest-socket`, sem credenciais do Azure e sem acesso à rede.

## Tasks

- [x] 1. Criar a estrutura do projeto
  - [x] 1.1 Criar a estrutura de diretórios e os arquivos de configuração
    - Criar os pacotes `app/`, `app/api/`, `app/core/`, `app/services/`, `app/prompts/`, `app/clients/`, `app/schemas/` com `__init__.py`, e os diretórios `tests/unit/`, `tests/property/`, `tests/api/`, `tests/docs/`
    - Criar `pyproject.toml` com dependências de execução (`fastapi`, `uvicorn`, `openai`, `python-multipart`, `pydantic` v2) e de desenvolvimento (`pytest`, `pytest-asyncio`, `httpx`, `hypothesis`, `pytest-socket`), configuração do pytest (`asyncio_mode`, `testpaths`) e registro do perfil Hypothesis com `max_examples` mínimo de 100
    - Criar `.env.example` com uma linha por variável (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `MAX_IMAGE_SIZE_BYTES`) usando só placeholders (`<seu-endpoint>`, `<sua-chave>`, `<nome-do-deployment>`, `<versao-da-api>`, `5242880`)
    - Criar `.gitignore` com `.env`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.hypothesis/`, `.mypy_cache/`, `.ruff_cache/`, `uploads/`, `output/`, `generated/`
    - _Requirements: 5.1, 5.2, 5.3, 6.5_

- [x] 2. Implementar esquemas, erros e configuração
  - [x] 2.1 Criar os esquemas Pydantic em `app/schemas/threat.py`
    - Implementar `StrideCategory` (valores com espaços, decisão D1), `Severity`, `Threat`, `ThreatAnalysis` e `ThreatReport(ThreatAnalysis)` com `extra="ignore"`, `NonEmptyText` (strip, 1 a 2000 caracteres) e listas limitadas a 50 itens
    - Definir a constante `HUMAN_REVIEW_NOTICE` em pt-BR
    - Manter a ordem dos campos: `components`, `data_flows`, `trust_boundaries`, `summary`, `threats`, `disclaimer`
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 4.8, 4.9_

  - [x] 2.2 Criar o tratamento de erros em `app/api/errors.py`
    - Implementar `AppError` (status, código, mensagem constante), `ErrorResponse` e os handlers para `AppError`, `RequestValidationError` (sem eco do valor enviado) e `Exception` (500 genérico com `internal_error`)
    - Mapear os códigos da tabela do design (`file_missing`, `file_empty`, `file_too_large`, `unsupported_media_type`, `signature_mismatch`, `context_too_long`, `service_not_configured`, `upstream_error`, `model_output_invalid`, `upstream_timeout`, `internal_error`)
    - Garantir que nenhuma mensagem interpole texto do Azure, endpoint, chave ou saída do modelo
    - _Requirements: 1.4, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.6, 4.4, 5.4, 5.5, 5.6, 5.7_

  - [x] 2.3 Criar `Settings` em `app/core/settings.py`
    - Implementar `Settings.from_env()` (dataclass imutável, `api_key` com `repr=False`, sem defaults para endpoint, chave e deployment) e `ensure_ready()` que levanta `AppError(503)` para valores ausentes, vazios ou só com espaços
    - Implementar `parse_max_image_size(raw)` com padrão de 5.242.880, regex `^[0-9]+$` após `strip()` e faixa de 1 a 20.971.520, senão 503
    - _Requirements: 5.1, 5.4, 5.5, 5.8_

  - [x] 2.4 Escrever teste de propriedade para campos obrigatórios de `Threat`
    - Arquivo: `tests/property/test_schema_props.py`
    - **Property 4: Campos obrigatórios de Threat**
    - Comentário de rastreio: `Feature: stride-threat-analysis-api, Property 4`
    - **Validates: Requirements 4.1**

  - [x] 2.5 Escrever teste de propriedade para enumerações exatas
    - Arquivo: `tests/property/test_schema_props.py`
    - **Property 5: Enumerações exatas e sensíveis a maiúsculas**
    - **Validates: Requirements 4.2**

  - [x] 2.6 Escrever teste de propriedade para o round trip do relatório
    - Arquivo: `tests/property/test_schema_props.py`
    - **Property 6: Round trip do relatório**
    - **Validates: Requirements 4.7**

  - [x] 2.7 Escrever teste de propriedade para os limites do esquema
    - Arquivo: `tests/property/test_schema_props.py`
    - **Property 7: Limites do esquema**
    - **Validates: Requirements 4.5**

  - [x] 2.8 Escrever teste de propriedade para a interpretação de `Max_Image_Size`
    - Arquivo: `tests/property/test_settings_props.py`
    - **Property 11: Interpretação de Max_Image_Size**
    - **Validates: Requirements 5.8**

  - [x] 2.9 Escrever testes unitários de esquemas, erros e configuração
    - Arquivos: `tests/unit/test_schemas.py`, `tests/unit/test_errors.py`, `tests/unit/test_settings.py`
    - Cobrir mapeamento do glossário (D1), `summary` com `threats` vazio, valores `"1e3"`, `"-5"`, `"5.0"`, `"0"`, `"20971521"`, `repr` sem a chave e corpo de erro sem segredos
    - _Requirements: 4.1, 4.2, 4.8, 5.1, 5.4, 5.5, 5.8_

- [~] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implementar validação de imagem e leitor de upload
  - [x] 4.1 Criar o `Image_Validator` em `app/services/image_validator.py`
    - Implementar `validate_image(content, declared_type, max_size)` na ordem: tipo declarado (415), tamanho acima do limite (413), arquivo vazio (400), assinatura divergente (415)
    - Normalizar o tipo declarado (minúsculas, ignorar parâmetros após `;`) e aceitar tamanho igual ao limite
    - Assinaturas: PNG `89 50 4E 47 0D 0A 1A 0A` e JPEG `FF D8 FF`
    - _Requirements: 1.6, 2.1, 2.2, 2.3, 2.5, 2.6_

  - [x] 4.2 Criar o leitor de upload em streaming em `app/api/upload.py`
    - Implementar `UploadedImage`, `ParsedRequest`, `CHUNK_SIZE` e `read_upload(request, max_image_size)` com `python_multipart.MultipartParser` sobre `request.stream()`, sem `UploadFile` e sem arquivos temporários
    - Interromper com 413 ao passar de `max_image_size` (memória limitada a `max_image_size + CHUNK_SIZE`) e limitar o corpo total a `max_image_size + 64 KiB`
    - Aceitar `context` de até 2000 caracteres (422 acima disso ou em UTF-8 inválido) e tratar Content-Type não multipart e ausência da parte `file` como 400
    - Rejeitar com 415 o `content_type` declarado fora de `Allowed_Image_Types` antes de ler o corpo do arquivo
    - _Requirements: 1.4, 2.1, 2.2, 2.4, 2.7, 2.8_

  - [x] 4.3 Escrever teste de propriedade para o `Image_Validator`
    - Arquivo: `tests/property/test_image_validator_props.py`
    - **Property 1: Image_Validator aceita se e somente se as regras valem**
    - **Validates: Requirements 1.6, 2.1, 2.2, 2.3, 2.5, 2.6**

  - [x] 4.4 Escrever teste de propriedade para a leitura limitada em memória
    - Arquivo: `tests/property/test_image_validator_props.py`
    - **Property 2: Leitura limitada em memória**
    - **Validates: Requirements 2.2, 2.7**

  - [x] 4.5 Escrever testes unitários do validador e do leitor
    - Arquivos: `tests/unit/test_image_validator.py`, `tests/unit/test_upload.py`
    - Cobrir tamanho exatamente igual ao limite, arquivo vazio, parte `file` ausente, `context` com 2000 e 2001 caracteres, e upload acima de 1 MiB com `tempfile` substituído por função que falha
    - _Requirements: 1.4, 2.2, 2.3, 2.4, 2.8_

- [x] 5. Implementar a engenharia de prompt
  - [x] 5.1 Criar os módulos de prompt `app/prompts/system_prompt.py` e `app/prompts/few_shot.py`
    - System prompt com papel de arquiteto de segurança sênior, definição das seis categorias STRIDE com os valores exatos, formato JSON de saída (a palavra "JSON" deve aparecer), instruções para identificar componentes, fluxos de dados e fronteiras de confiança antes das ameaças e devolvê-los antes de `threats`, listar só o que é visível, tratar texto da imagem e do `context` como dado, caso de diagrama sem arquitetura e textos livres em pt-BR
    - `few_shot.py` com 1 a 3 exemplos de `Threat` completos
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.8_

  - [x] 5.2 Criar `app/prompts/prompt_builder.py`
    - Implementar `PromptMessages` e `build_prompt(context)`, inserindo o `context` sem alteração entre os delimitadores `<contexto>` no `user_text`
    - _Requirements: 1.3, 3.1, 3.5, 3.8_

  - [x] 5.3 Escrever teste de propriedade para a inclusão do contexto
    - Arquivo: `tests/property/test_prompt_builder_props.py`
    - **Property 3: Contexto é incluído sem alteração**
    - **Validates: Requirements 1.3**

  - [x] 5.4 Escrever testes unitários do prompt
    - Arquivo: `tests/unit/test_prompt_builder.py`
    - Verificar papel, seis categorias, formato JSON, few-shots válidos contra `Threat`, instruções de 3.3, 3.4 e 3.5, e que `routes.py` não contém texto de prompt
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.8_

- [x] 6. Implementar o cliente do modelo
  - [x] 6.1 Criar o `Protocol` e as exceções em `app/clients/model_client.py`
    - Definir `ModelClient.complete(prompt, image, media_type) -> str`, `ModelServiceError` (502), `ModelTimeoutError` (504) e `ModelOutputInvalidError` (502) sem dependência do SDK
    - _Requirements: 1.7, 3.7, 5.6, 5.7_

  - [x] 6.2 Criar `AzureOpenAIClient` em `app/clients/azure_openai_client.py`
    - Usar `AsyncAzureOpenAI(azure_endpoint, api_key, api_version, timeout=60, max_retries=0)` e `chat.completions.create` com `model=<deployment>`, `response_format={"type": "json_object"}`, `temperature=0.1`, `max_tokens=4096` e a imagem como data URL base64 em parte `image_url`
    - Envolver a chamada em `asyncio.timeout(60)` (estouro vira `ModelTimeoutError`), converter exceções do SDK em `ModelServiceError` sem repassar a mensagem original e tratar `finish_reason` diferente de `stop`, conteúdo vazio ou recusa como `ModelOutputInvalidError`
    - Criar a fábrica `get_model_client()` a partir de `Settings` já validado
    - _Requirements: 1.7, 3.6, 3.7, 5.5, 5.6, 5.7_

  - [x] 6.3 Criar a infraestrutura de testes em `tests/conftest.py`
    - Fixture `autouse` com `pytest-socket` (`disable_socket()`), remoção de `AZURE_OPENAI_*` e `MAX_IMAGE_SIZE_BYTES` com `monkeypatch.delenv`, e substituição de `AzureOpenAIClient.__init__` por função que falha com mensagem de acesso proibido
    - Implementar `FakeModelClient` (resposta ou exceção configurável, contador de chamadas e argumentos registrados) e helpers compartilhados de asserção para cenários de falha
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 6.4 Escrever testes unitários do cliente Azure com SDK falso
    - Arquivo: `tests/unit/test_azure_client.py`
    - Verificar `response_format` `json_object`, temperatura em [0, 0.2], `max_retries=0`, timeout (fake que dorme resulta em 504), erro do SDK com texto marcador resulta em 502 sem o marcador, e `finish_reason` `length` ou conteúdo vazio resulta em saída inválida
    - _Requirements: 3.6, 3.7, 5.6, 5.7_

- [x] 7. Implementar validação da resposta e serviço de análise
  - [x] 7.1 Criar o `Response_Validator` em `app/services/response_validator.py`
    - Implementar `validate_model_output(raw)` com `ThreatAnalysis.model_validate_json`, montagem de `ThreatReport` com `disclaimer=HUMAN_REVIEW_NOTICE` e conversão de qualquer falha em `AppError(502, "model_output_invalid")` com mensagem fixa
    - Registrar em log só a categoria e a quantidade de erros, nunca o conteúdo bruto nem `input` dos erros
    - _Requirements: 4.3, 4.4, 4.6, 4.8, 4.9_

  - [x] 7.2 Criar o `Analysis_Service` em `app/services/analysis_service.py`
    - Implementar `AnalysisService(client, max_image_size).analyze(image, context)` com a sequência `validate_image` → `build_prompt` → `client.complete` → `validate_model_output`, sem importar `fastapi` e sem segunda chamada ao modelo em caso de saída inválida
    - _Requirements: 1.1, 1.2, 1.6, 3.7, 4.3, 4.4_

  - [x] 7.3 Escrever teste de propriedade para campos desconhecidos
    - Arquivo: `tests/property/test_response_validator_props.py`
    - **Property 8: Campos desconhecidos são descartados**
    - **Validates: Requirements 4.9**

  - [x] 7.4 Escrever teste de propriedade para o `disclaimer`
    - Arquivo: `tests/property/test_response_validator_props.py`
    - **Property 9: Disclaimer é sempre o aviso da API**
    - **Validates: Requirements 4.6**

  - [x] 7.5 Escrever testes unitários do validador de resposta e do serviço
    - Arquivos: `tests/unit/test_response_validator.py`, `tests/unit/test_analysis_service.py`
    - Cobrir JSON inválido, violação de esquema, diagrama sem arquitetura (`threats` vazio com `summary`), erro do fake propagado, imagem inválida sem chamar o fake e exatamente uma chamada ao fake nos demais casos
    - _Requirements: 1.2, 1.6, 3.7, 4.3, 4.4, 4.8_

- [~] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implementar a camada HTTP e ligar os componentes
  - [x] 9.1 Criar o logging em `app/core/logging.py`
    - Configurar logs estruturados com `request_id`, código do erro e duração, sem registrar `api_key`, bytes da imagem, `context`, saída bruta do modelo nem mensagens de exceção do SDK
    - _Requirements: 5.5_

  - [x] 9.2 Criar `app/api/routes.py` e `app/main.py`
    - `create_app()` registrando os handlers de erro, o router e o logging
    - `POST /api/v1/analyze`: `Settings.from_env().ensure_ready()` primeiro (503), depois `read_upload`, `Depends(get_model_client)` e `AnalysisService`, devolvendo 200 com `ThreatReport`; descrever o corpo multipart em `openapi_extra` para que `/docs` mostre `file` e `context`
    - `GET /health` retornando `{"status": "ok"}` sem tocar `Settings` nem o cliente Azure
    - Nenhum texto de prompt em `routes.py`
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 5.4, 5.5, 5.8, 6.8_

  - [x] 9.3 Escrever teste de propriedade para saída inválida do modelo
    - Arquivo: `tests/property/test_response_validator_props.py`
    - **Property 10: Saída inválida nunca vaza e não gera nova chamada**
    - Criar o app e o fake dentro do corpo do teste, ou usar `suppress_health_check=[HealthCheck.function_scoped_fixture]`
    - **Validates: Requirements 3.7, 4.4**

  - [x] 9.4 Escrever teste de propriedade para configuração incompleta
    - Arquivo: `tests/property/test_settings_props.py`
    - **Property 12: Configuração incompleta resulta em 503 sem chamada**
    - **Validates: Requirements 5.4**

  - [x] 9.5 Escrever os testes de API por cenário
    - Arquivo: `tests/api/test_analyze.py`, usando `httpx.AsyncClient` com `ASGITransport` e `app.dependency_overrides`
    - Um teste por cenário: sucesso, tipo inválido (415), arquivo grande demais (413), arquivo vazio (400), assinatura divergente (415), JSON inválido do modelo (502), violação de esquema (502) e erro do Azure (502), além de timeout (504), `file` ausente (400), `context` com 2000 e 2001 caracteres, `/docs` (200), `/health` sem chamadas ao fake e diagrama sem arquitetura
    - Em cada falha, afirmar status e `code`, ausência de `threats` e, para falhas do `Image_Validator`, zero chamadas ao fake
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.6, 4.4, 4.8, 5.6, 5.7, 6.3, 6.4, 6.8_

  - [x] 9.6 Escrever testes de segurança e da infraestrutura de testes
    - Arquivos: `tests/api/test_secrets.py`, `tests/unit/test_test_infra.py`
    - Usar chave sentinela e varrer `caplog`, corpo e headers em todos os cenários de falha; confirmar que abrir um socket e instanciar o cliente real falham nos testes
    - _Requirements: 5.5, 6.1, 6.2_

- [~] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Configurar a integração contínua
  - [x] 11.1 Criar `.github/workflows/ci.yml`
    - Disparar em `pull_request` e em `push` com `branches-ignore: [main]`, instalar as dependências e executar `pytest`, sem nenhum segredo do Azure; falha de teste termina o job com status de falha
    - _Requirements: 6.6, 6.7_

  - [x] 11.2 Escrever testes de fumaça do repositório
    - Arquivo: `tests/docs/test_repo_config.py`
    - Verificar que `.env.example` lista as mesmas variáveis lidas por `Settings`, que `.gitignore` contém as entradas exigidas e que `ci.yml` define os gatilhos e não referencia segredos do Azure
    - _Requirements: 5.2, 5.3, 6.6, 6.7_

- [x] 12. Criar documentação, exemplos, imagens e licença
  - [x] 12.1 Criar o arquivo `LICENSE` na raiz
    - Texto completo da licença MIT, com o nome do titular dos direitos
    - _Requirements: 7.9_

  - [x] 12.2 Criar a imagem de exemplo e os arquivos de `examples/`
    - Gerar `images/exemplo-arquitetura.png` (diagrama simples de três camadas) com um script em `tools/gerar_diagrama.py`, adicionando a dependência de desenvolvimento necessária ao `pyproject.toml`
    - Criar em `examples/` um arquivo de requisição (comando `curl` ou arquivo `.http`) que envia essa mesma imagem, e `examples/resposta-exemplo.json` com uma resposta válida contra `ThreatReport`
    - _Requirements: 7.4, 7.6, 7.7_

  - [x] 12.3 Criar os quatro arquivos em `docs/`, em pt-BR
    - `docs/decisoes-de-arquitetura.md` (incluindo D1 a D7), `docs/engenharia-de-prompt.md`, `docs/consideracoes-de-seguranca.md` e `docs/licoes-aprendidas.md`, cada um com ao menos uma seção titulada
    - Usar apenas placeholders para endpoint, chave e nome de recurso
    - _Requirements: 7.3, 7.7, 7.8_

  - [x] 12.4 Criar o `README.md` em pt-BR
    - Onze seções tituladas: objetivo, arquitetura, metodologia STRIDE, pré-requisitos, configuração do Azure OpenAI, instalação, execução, exemplos de requisição e resposta, técnicas de engenharia de prompt, estrutura do projeto e limitações
    - Seção própria com o `HUMAN_REVIEW_NOTICE` e o aviso de uso ético e defensivo (somente sistemas próprios ou autorizados)
    - Links relativos para os quatro arquivos de `docs/` e para os arquivos de `examples/`, e referência à imagem em `images/`; referenciar screenshots apenas se existirem em `images/`
    - Configuração do Azure somente com placeholders (`<seu-endpoint>`, `<sua-chave>`, `<nome-do-deployment>`)
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6, 7.7_

  - [x] 12.5 Escrever testes de fumaça da documentação
    - Arquivo: `tests/docs/test_docs.py`
    - Verificar as onze seções e a seção do aviso no `README.md`, links relativos válidos para `docs/` e `examples/`, a existência da imagem e do `LICENSE`, que `examples/resposta-exemplo.json` valida contra `ThreatReport`, e uma varredura de padrões de endpoint e chave reais em todo o repositório
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.8, 7.9_

- [~] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Publicar no Git e no GitHub
  - [x] 14.1 Verificar o repositório antes do commit
    - Confirmar com `git status` e `git remote -v` o repositório e o remoto de destino; confirmar que `.env` está ignorado (`git check-ignore .env`) e que nenhum arquivo de credencial, chave ou token está no working tree a ser commitado
    - Sinalizar ao usuário e aguardar confirmação antes de staging de qualquer arquivo com risco de segredo; `.env` nunca é commitado
    - Executar `pytest` e a varredura de segredos e só seguir se passarem
    - _Requirements: 8.3, 8.4_

  - [-] 14.2 Criar o commit e publicar
    - Adicionar os arquivos um a um com `git add <arquivo>`, nunca `git add .` nem `git add -A`, sem usar `--no-verify`
    - Projeto novo e pessoal: criar o repositório público `Gtvnv/stride-threat-analysis-api` (por exemplo `gh repo create Gtvnv/stride-threat-analysis-api --public`), confirmar que o remoto é `github.com/Gtvnv/*`, e fazer o commit inicial e o push direto na `main` com `git push -u origin main`; esta é a única exceção permitida
    - Qualquer outro repositório (outra conta, organização ou terceiro): criar uma branch com prefixo `feature/`, `fix/`, `hotfix/`, `chore/`, `refactor/`, `docs/` ou `test/`, fazer `git push -u origin <branch>`, abrir um Pull Request com ao menos 1 revisor humano e recusar qualquer escrita direta na `main`
    - Nunca usar `push --force`, `reset --hard` nem reescrever o histórico da `main`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido.
- Cada tarefa referencia requisitos específicos para rastreabilidade.
- Os 12 testes de propriedade (Properties 1 a 12) usam Hypothesis com no mínimo 100 exemplos, um teste por propriedade, e comentário `Feature: stride-threat-analysis-api, Property N`.
- Testes de propriedade e unitários validam, respectivamente, propriedades universais e exemplos e casos de borda.
- A tarefa 14 só vale para publicação do projeto; o trabalho de implementação não deve modificar `requirements.md` nem `design.md`.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "9.1", "11.1", "12.1"] },
    { "id": 2, "tasks": ["2.3", "2.4", "4.1", "4.2", "5.1", "7.1", "12.2"] },
    { "id": 3, "tasks": ["2.5", "2.8", "2.9", "4.3", "5.2", "7.3"] },
    { "id": 4, "tasks": ["2.6", "4.4", "4.5", "5.3", "5.4", "6.1", "7.4"] },
    { "id": 5, "tasks": ["2.7", "6.2", "7.2"] },
    { "id": 6, "tasks": ["6.3", "6.4", "7.5", "9.2"] },
    { "id": 7, "tasks": ["9.3", "9.4", "9.5", "9.6", "11.2", "12.3"] },
    { "id": 8, "tasks": ["12.4"] },
    { "id": 9, "tasks": ["12.5"] },
    { "id": 10, "tasks": ["14.1"] },
    { "id": 11, "tasks": ["14.2"] }
  ]
}
```
