# Lições aprendidas

Anotações sobre o que funcionou, o que exigiu ajuste e o que ficou como ponto de atenção durante a construção da STRIDE Threat Analysis API.

## O que funcionou bem

- **Cliente do modelo atrás de um `Protocol`.** O `ModelClient` permitiu testar toda a lógica com um fake, sem credenciais e sem rede. O `conftest.py` reforça isso: bloqueia sockets, limpa as variáveis do Azure e faz o `AzureOpenAIClient` real falhar se alguém tentar instanciá-lo.
- **Esquema como contrato da saída do modelo.** Tratar a resposta do LLM como dado não confiável e validá-la com Pydantic tornou o comportamento previsível. Qualquer desvio vira 502 genérico.
- **Separar `ThreatAnalysis` de `ThreatReport`.** O `disclaimer` entra só pela API, e campos extras do modelo somem com `extra="ignore"`, sem código adicional.
- **Mensagens de erro constantes.** Um catálogo único (`ERROR_CATALOG`) facilita testar que nada vaza (marcadores únicos em corpo e headers) e mantém o formato do erro uniforme.
- **Testes de propriedade.** Hypothesis, com ao menos 100 exemplos, cobriu bem o `Image_Validator` (tamanho e assinatura), o round trip do relatório, os limites do esquema e a interpretação de `MAX_IMAGE_SIZE_BYTES`. Esse tipo de teste exercita casos de borda que exemplos escritos à mão costumam deixar de fora, como o tamanho exatamente igual ao limite.

## O que exigiu ajuste

- **`UploadFile` não serve para o requisito de memória e disco.** O Starlette lê o corpo todo e grava em arquivo temporário acima de 1 MiB. A solução foi um leitor multipart em streaming sobre `request.stream()`. O custo é que a rota passou a ler o corpo manualmente e a documentar o formulário em `openapi_extra`.
- **Configuração lida a cada análise.** Falhar na inicialização seria mais simples, mas impediria `/health` e `/docs` com configuração incompleta. A leitura por requisição também afeta os testes: a rota chama `Settings.from_env().ensure_ready()` diretamente, então testes que trocam o cliente por um fake precisam definir variáveis de ambiente falsas. Sem elas a resposta é 503.
- **Código `invalid_request` (422).** O catálogo original não previa erros de validação do FastAPI nem `context` com UTF-8 inválido. Foi acrescentado um código genérico, sem eco do valor enviado.
- **Bloqueio de rede no Windows.** O event loop do asyncio cria um `socketpair` em loopback, e `disable_socket()` impediria isso. No Windows, o `conftest.py` permite só `127.0.0.1` e `::1`. Nos demais sistemas, bloqueia tudo, exceto sockets Unix.
- **Retentativas do SDK.** O padrão do SDK refaz chamadas, o que contradiz a regra de uma única chamada por análise e o teto de 60 s. Foi preciso `max_retries=0` e um `asyncio.timeout` no chamador.
- **Formato das categorias.** O glossário usa underscore e o prompt usa espaços. A decisão D1 fixou o valor com espaços no JSON e mapeou os membros do enum com underscore.
- **`response_format` JSON.** O modo `json_object` exige a palavra "JSON" nas mensagens e garante só JSON sintaticamente válido. O esquema continua obrigatório.
- **Truncamento.** Quando `finish_reason` é `length` ou `content_filter`, o JSON pode vir incompleto. O cliente trata qualquer `finish_reason` diferente de `stop` como saída inválida.

## Prompt

- Pedir componentes, fluxos e fronteiras antes das ameaças ajuda o modelo a se ancorar no diagrama.
- A regra de listar só o que é visível reduz componentes inventados, mas não elimina o problema.
- Exemplos few-shot melhoram o formato, e há o risco de o modelo copiá-los. Por isso o prompt avisa que eles só ilustram o formato.
- Prompt não substitui validação. A defesa contra injeção de prompt é uma mitigação, e a revisão humana continua necessária.

## Segurança

- Logs com lista de campos permitidos são mais seguros do que tentar filtrar segredos depois. O formatter não emite o texto da mensagem nem o traceback.
- O log de `ValidationError` deve guardar só a contagem de erros. `exc.errors()` carrega o `input` com o conteúdo bruto do modelo.
- Verificar assinatura de arquivo é barato e pega divergências comuns, mas não substitui isolamento no serviço que processa a imagem.

## Pontos de atenção para evolução

- Adicionar autenticação e limitação de taxa antes de expor a API fora do ambiente local.
- Avaliar uma fila ou limite de concorrência para controlar custo e latência.
- Medir a qualidade da análise com um conjunto de diagramas de referência e revisão por especialistas.
- Se o Azure OpenAI mudar o suporte a versões da API, revisar `AZURE_OPENAI_API_VERSION` (`<versao-da-api>`) e o deployment (`<nome-do-deployment>`).

## Fluxo de trabalho

- Os testes rodam sem segredos localmente e no GitHub Actions (em pull requests e em pushes para branches diferentes de `main`).
- Commits devem nomear os arquivos individualmente, e arquivos com possível segredo (`.env`, JSON de credenciais, chaves) não devem ser versionados.
