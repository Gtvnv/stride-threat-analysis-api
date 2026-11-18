# Considerações de segurança

Este documento descreve as proteções da API e os riscos que continuam abertos. O projeto tem finalidade educacional e defensiva. Use-o apenas em diagramas de sistemas que você possui ou está autorizado a avaliar.

## Uso ético e revisão humana

A análise é gerada por um modelo de linguagem e pode conter erros ou omissões. Todo `Threat_Report` traz o campo `disclaimer` com o aviso de revisão humana. O valor é definido pela API e sobrescreve qualquer `disclaimer` presente na saída do modelo. Trate o relatório como ponto de partida para a revisão de um profissional, nunca como parecer final.

## Segredos e configuração

- Endpoint, chave, deployment, versão da API e limite de imagem vêm só de variáveis de ambiente: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` e `MAX_IMAGE_SIZE_BYTES`.
- Não há valor padrão para endpoint, chave e deployment.
- O `.env.example` contém apenas placeholders (`<seu-endpoint>`, `<sua-chave>`, `<nome-do-deployment>`, `<versao-da-api>`). O arquivo `.env` real está no `.gitignore` e não deve ser versionado.
- O campo `api_key` do `Settings` tem `repr=False`. A chave não aparece em logs, corpos de resposta nem headers.
- Configuração ausente ou inválida resulta em 503 com mensagem genérica, sem chamar o Azure, e a API continua atendendo `/health` e `/docs`.
- Se publicar uma cópia do projeto, confirme que nenhum arquivo contém endpoint, chave ou nome de recurso reais. Use sempre placeholders na documentação.

## Validação do upload (fronteira de confiança)

O arquivo enviado é tratado como não confiável. As regras são aplicadas antes de qualquer chamada ao Azure:

| Verificação | Resultado |
|-------------|-----------|
| Tipo declarado fora de `image/png` e `image/jpeg` | 415 `unsupported_media_type` |
| Tamanho acima de `Max_Image_Size` (padrão 5 MiB, máximo 20 MiB) | 413 `file_too_large` |
| Arquivo vazio | 400 `file_empty` |
| Parte `file` ausente ou corpo não multipart | 400 `file_missing` |
| Assinatura (magic bytes) diferente do tipo declarado | 415 `signature_mismatch` |
| `context` acima de 2000 caracteres | 422 `context_too_long` |

- A assinatura PNG (`89 50 4E 47 0D 0A 1A 0A`) e a JPEG (`FF D8 FF`) são conferidas independentemente do tipo declarado.
- A leitura é em streaming e para ao exceder o limite. A memória fica limitada ao tamanho máximo mais um chunk, e o corpo total tem teto de `Max_Image_Size` + 64 KiB.
- A imagem existe só em memória. Não é gravada em disco, não é guardada em cache e sai de escopo ao fim da requisição.
- A verificação de assinatura não prova que a imagem é inofensiva. Ela confirma só os primeiros bytes. A API não decodifica nem reprocessa a imagem, e repassa os bytes ao serviço de IA.

## Saída do modelo é dado não confiável

- O conteúdo do modelo só chega ao cliente depois de passar pelo esquema Pydantic. Enumerações exigem valor exato, e os limites são 50 ameaças, 50 itens por lista e 2000 caracteres por texto.
- Qualquer falha (JSON inválido, violação do esquema, resposta vazia, recusa, `finish_reason` diferente de `stop`) resulta em 502 `model_output_invalid` com mensagem constante, sem a saída bruta e sem relatório parcial.
- Campos desconhecidos são descartados.
- Não há nova chamada ao modelo após uma saída inválida.

## Injeção de prompt

O texto dentro da imagem e o campo `context` podem tentar dar instruções ao modelo. O prompt os declara como dados e manda ignorar instruções contidas neles, e o `context` vai entre delimitadores. Essa defesa é uma mitigação e não uma garantia. Por isso a saída é validada pelo esquema e revisada por uma pessoa. Um atacante ainda pode influenciar o conteúdo textual dos campos (por exemplo, a descrição de uma ameaça) dentro do formato válido.

## Mensagens de erro genéricas

As mensagens de erro são constantes (`ERROR_CATALOG`). Elas nunca incluem texto do Azure, endpoint, chave, valor enviado pelo cliente ou saída do modelo.

- Erro do serviço Azure: 502 `upstream_error`.
- Timeout de 60 s: 504 `upstream_timeout`, com a chamada cancelada.
- Erro de validação do FastAPI: 422 `invalid_request`, sem eco do valor enviado.
- Exceção inesperada: 500 `internal_error`.

## Logs

Os logs são JSON, emitidos por `app/core/logging.py`, e só aceitam campos de uma lista permitida (`event`, `error_code`, `duration_ms`, `status_code`, `method`, `path`, `exception_type`, `error_count`, `model_calls`, `request_id`). O middleware de requisições registra `request_completed` ou `request_failed` com `request_id` e duração.

Nunca são registrados: chave de API, bytes da imagem, `context`, saída bruta do modelo e mensagens de exceção do SDK. Em falhas de validação do modelo, o log guarda só a categoria e a contagem de erros.

## Testes sem credenciais

A suíte roda sem variáveis do Azure e com a rede bloqueada. Tentar abrir conexão ou instanciar o cliente real do Azure faz o teste falhar. O CI no GitHub Actions executa os testes sem segredos.

## Limitações e riscos residuais

- A API não tem autenticação, autorização nem limitação de taxa. Se for exposta além de um ambiente local, coloque-a atrás de um gateway com essas proteções.
- Cada requisição aceita pode consumir cota e custo do deployment no Azure.
- O limite de 60 s por chamada ao modelo não substitui controle de concorrência.
- A qualidade da análise depende do modelo e da legibilidade do diagrama. Diagramas ambíguos podem gerar ameaças incorretas ou omitir riscos reais.
- Imagens de diagramas podem conter informação sensível. Elas são enviadas ao serviço Azure OpenAI configurado, então avalie as políticas de dados do seu recurso antes de enviar material confidencial.
