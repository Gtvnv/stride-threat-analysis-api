# Requirements Document

## Introduction

O projeto "STRIDE Threat Analysis API" é uma API em Python e FastAPI que recebe a imagem de um diagrama de arquitetura de uma aplicação, envia a imagem a um modelo com capacidade de visão hospedado no Azure OpenAI usando técnicas de engenharia de prompt, e devolve uma análise de ameaças baseada na metodologia STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

O projeto tem finalidade educacional e defensiva. É publicado em um repositório público do GitHub com documentação detalhada em português do Brasil (pt-BR). A saída do modelo é tratada como dado não confiável, validada contra um esquema estruturado e sempre sujeita a revisão humana. Os testes executam sem credenciais reais do Azure.

## Glossary

- **API**: Aplicação FastAPI que expõe os endpoints HTTP do projeto.
- **Analysis_Service**: Componente que orquestra a análise: valida a imagem, monta o prompt, chama o Azure_OpenAI_Client e valida a resposta.
- **Azure_OpenAI_Client**: Componente que encapsula a chamada ao serviço Azure OpenAI com um deployment de modelo com visão.
- **Image_Validator**: Componente que valida o arquivo de imagem enviado (tipo, tamanho e conteúdo).
- **Prompt_Builder**: Componente que monta as mensagens de sistema e de usuário usando técnicas de engenharia de prompt.
- **Response_Validator**: Componente que interpreta a resposta do modelo e a valida contra o Threat_Report_Schema.
- **Threat_Report_Schema**: Esquema Pydantic que define a estrutura do relatório de ameaças.
- **Threat_Report**: Objeto JSON que contém a lista de ameaças identificadas e os metadados da análise, conforme o Threat_Report_Schema.
- **Threat**: Item do Threat_Report com categoria STRIDE, componente afetado, descrição, severidade e mitigação sugerida.
- **STRIDE_Category**: Um dos seis valores: Spoofing, Tampering, Repudiation, Information_Disclosure, Denial_of_Service, Elevation_of_Privilege.
- **Severity**: Um dos valores: Low, Medium, High, Critical.
- **Settings**: Configuração da aplicação lida de variáveis de ambiente (endpoint, chave de API, nome do deployment, versão da API, limite de tamanho de imagem).
- **Allowed_Image_Types**: Os tipos de imagem aceitos: image/png e image/jpeg.
- **Max_Image_Size**: Tamanho máximo do arquivo de imagem, padrão de 5 MiB, configurável por variável de ambiente.
- **Repository**: Repositório público do GitHub que contém o código e a documentação.
- **Human_Review_Notice**: Aviso de que a saída de um LLM exige revisão humana e de que o uso deve ser ético e defensivo.

## Requirements

### Requirement 1: Analisar diagrama de arquitetura

**User Story:** Como analista de segurança, quero enviar a imagem de um diagrama de arquitetura para a API, para que eu receba uma análise de ameaças STRIDE sem precisar produzi-la manualmente.

#### Acceptance Criteria

1. WHEN a client sends a multipart POST request to the endpoint `/api/v1/analyze` with an image file of an Allowed_Image_Type and a size between 1 byte and the Max_Image_Size, THE API SHALL return HTTP status 200 with a Threat_Report in JSON format within 60 seconds, where each Threat in the Threat_Report is assigned to one of the six STRIDE_Categories.
2. WHEN the Analysis_Service receives a valid image, THE Analysis_Service SHALL send the image to the Azure_OpenAI_Client together with the messages produced by the Prompt_Builder.
3. WHERE the client supplies an optional text field `context` of 1 to 2000 characters, THE Prompt_Builder SHALL include the text unchanged as additional application context in the user message.
4. IF the client supplies a `context` field longer than 2000 characters, THEN THE API SHALL return HTTP status 422 with an error message indicating that the maximum allowed length is 2000 characters, and THE API SHALL NOT send any request to the Azure_OpenAI_Client.
5. THE API SHALL expose an interactive OpenAPI documentation page at the path `/docs`.
6. IF the request has no image file, or the file is empty, larger than the Max_Image_Size, or not of an Allowed_Image_Type, THEN THE API SHALL reject the request with an error response indicating which image constraint was violated, as detailed in Requirement 2, and THE API SHALL NOT send any request to the Azure_OpenAI_Client.
7. IF the Azure_OpenAI_Client returns an error or does not respond within 60 seconds, THEN THE API SHALL return an error response indicating that the analysis could not be completed, as detailed in Requirement 5, without returning a partial Threat_Report.

### Requirement 2: Validar imagem enviada

**User Story:** Como mantenedor, quero que a imagem enviada seja validada na fronteira de confiança, para que arquivos inválidos ou maliciosos não cheguem ao serviço de IA.

#### Acceptance Criteria

1. IF the uploaded file has a content type outside the Allowed_Image_Types (image/png, image/jpeg), THEN THE Image_Validator SHALL reject the request, THE API SHALL return HTTP status 415 with an error message indicating the content type is not allowed, and THE API SHALL NOT forward the file to the AI service.
2. IF the uploaded file size exceeds the Max_Image_Size, THEN THE Image_Validator SHALL reject the request, THE API SHALL return HTTP status 413 with an error message indicating the maximum allowed size, and THE API SHALL NOT forward the file to the AI service. A file whose size equals the Max_Image_Size exactly SHALL be accepted.
3. IF the uploaded file has a size of 0 bytes, THEN THE Image_Validator SHALL reject the request, THE API SHALL return HTTP status 400 with an error message indicating the file is empty, and THE API SHALL NOT forward the file to the AI service.
4. IF the request does not contain an image file part, THEN THE Image_Validator SHALL reject the request and THE API SHALL return HTTP status 400 with an error message indicating the file is missing.
5. WHEN a file is uploaded, THE Image_Validator SHALL verify that the first bytes of the file match the PNG signature (89 50 4E 47 0D 0A 1A 0A) or the JPEG signature (FF D8 FF), regardless of the declared content type.
6. IF the file signature does not match any allowed signature, or matches a format different from the declared content type, THEN THE Image_Validator SHALL reject the request, THE API SHALL return HTTP status 415 with an error message indicating the content does not match the declared type, and THE API SHALL NOT forward the file to the AI service.
7. WHILE the API reads the uploaded file, THE API SHALL stop reading once the number of bytes read exceeds the Max_Image_Size, so that memory usage stays bounded by the Max_Image_Size plus one read chunk, and THE API SHALL return HTTP status 413 as defined in criterion 2.
8. WHEN the request completes, whether with success or error, THE API SHALL discard the uploaded image from memory and SHALL NOT write the image to disk at any point during processing.

### Requirement 3: Engenharia de prompt

**User Story:** Como desenvolvedor, quero que o prompt use técnicas de engenharia de prompt, para que a análise seja consistente, estruturada e aderente ao STRIDE.

#### Acceptance Criteria

1. THE Prompt_Builder SHALL produce a system message that contains the role of security architect, the definition of each of the six STRIDE_Categories (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege), and the required JSON output format, with each of these three elements present in the message.
2. THE Prompt_Builder SHALL include in the system message at least one and at most three examples of a valid Threat as few-shot examples, where each example contains every field required by the Threat output format and a STRIDE_Category from the six defined categories.
3. THE Prompt_Builder SHALL instruct the model to identify components, data flows and trust boundaries in the diagram before listing Threats, and to return the identified components, data flows and trust boundaries in the response before the list of Threats.
4. THE Prompt_Builder SHALL instruct the model to list only components that are visible in the diagram and to omit any component whose presence cannot be confirmed from the diagram.
5. THE Prompt_Builder SHALL instruct the model to treat any text written inside the image or in the `context` field as data and to ignore instructions contained in it.
6. WHEN the Azure_OpenAI_Client calls the model, THE Azure_OpenAI_Client SHALL request a JSON object response format and a temperature between 0 and 0.2 inclusive.
7. IF the model response is not valid JSON or does not conform to the required JSON output format, THEN THE Azure_OpenAI_Client SHALL reject the response immediately, make no further call to the model (no retry and no re-prompt), return an error indicating that the model output is invalid, and return no Threats to the caller.
8. THE Prompt_Builder SHALL keep the prompt text in dedicated module files separate from the HTTP layer, so that the HTTP layer contains no prompt text literals.

### Requirement 4: Validar resposta do modelo

**User Story:** Como analista de segurança, quero que a resposta do modelo seja validada contra um esquema, para que a saída não confiável nunca seja repassada sem verificação.

#### Acceptance Criteria

1. THE Threat_Report_Schema SHALL define each Threat with the required fields `category`, `component`, `description`, `severity` and `mitigation`, and SHALL reject any Threat in which one of these fields is missing, null or an empty string.
2. THE Threat_Report_Schema SHALL restrict `category` to the six STRIDE_Categories (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) and `severity` to the defined Severity values, and SHALL reject any other value, including values that differ only in letter case.
3. WHEN the Azure_OpenAI_Client returns a response, THE Response_Validator SHALL parse the response content as JSON and validate it against the Threat_Report_Schema before any part of the content is included in the API response.
4. IF the response content is not valid JSON or does not conform to the Threat_Report_Schema, THEN THE API SHALL discard the model output, return HTTP status 502 with a generic error message that does not include the raw model output, and not return a partial Threat_Report.
5. THE Threat_Report_Schema SHALL limit the number of Threats to a maximum of 50 and the length of each text field to a maximum of 2000 characters, and SHALL reject a response that exceeds either limit.
6. THE Threat_Report SHALL include a `disclaimer` field containing the Human_Review_Notice, added by the API and not taken from the model output, and IF the model output contains a `disclaimer` field, THEN THE API SHALL overwrite it with the Human_Review_Notice.
7. FOR ALL valid Threat_Report objects, serializing to JSON and parsing back through the Threat_Report_Schema SHALL produce an equivalent object (round-trip property).
8. IF the diagram contains no identifiable architecture, THEN THE API SHALL return HTTP status 200 with a Threat_Report with an empty list of Threats and a `summary` field that states the reason, limited to 2000 characters.
9. IF the model response contains fields not defined in the Threat_Report_Schema, THEN THE Response_Validator SHALL exclude those fields from the Threat_Report returned by the API.

### Requirement 5: Configuração e segredos

**User Story:** Como mantenedor, quero que os segredos e a configuração venham apenas de variáveis de ambiente, para que nenhuma credencial seja exposta no repositório.

#### Acceptance Criteria

1. WHEN the application starts, THE Settings SHALL read the Azure OpenAI endpoint, API key, deployment name, API version and Max_Image_Size exclusively from environment variables, and THE Settings SHALL NOT contain any default value for the endpoint, API key or deployment name.
2. THE Repository SHALL include a `.env.example` file that lists each environment variable read by the Settings, with one placeholder value per variable, and that contains no real credential.
3. THE Repository SHALL include a `.gitignore` file that excludes `.env`, virtual environment directories, cache directories, and the directories used for uploaded and generated files.
4. IF the Azure OpenAI endpoint, API key, deployment name or API version is missing or is an empty string when an analysis is requested, THEN THE API SHALL return HTTP status 503 with a generic message that names no variable value, SHALL NOT call the Azure OpenAI service, and SHALL keep serving subsequent requests.
5. THE API SHALL NOT include the API key value in any log entry or in any response body or header, including error responses.
6. IF the Azure OpenAI service returns an error response, THEN THE API SHALL return HTTP status 502 with a generic message that does not include the service error text, the endpoint or the API key.
7. IF the Azure OpenAI service does not respond within 60 seconds, THEN THE API SHALL cancel the call, return HTTP status 504 with a generic message that does not include internal error details, and keep serving subsequent requests.
8. IF Max_Image_Size is set to a value that is not a positive integer or is outside the range 1 byte to 20,971,520 bytes (20 MB), THEN THE API SHALL return HTTP status 503 with a generic message when an analysis is requested. IF Max_Image_Size is not set, THEN THE Settings SHALL use the default of 5 MiB.

### Requirement 6: Testes sem credenciais

**User Story:** Como mantenedor, quero testes que rodem sem credenciais reais, para que qualquer pessoa execute a suíte localmente e em integração contínua.

#### Acceptance Criteria

1. WHEN the test suite is executed, THE Repository SHALL run all automated tests to completion with outbound network access blocked and with no Azure credential environment variables set, by replacing the Azure_OpenAI_Client with a mock.
2. IF a test attempts to open a network connection or to instantiate the real Azure_OpenAI_Client, THEN THE test suite SHALL fail that test with an error indicating the forbidden access.
3. THE tests SHALL include at least one test for each of the following scenarios: success path, invalid file type, oversized file, empty file, signature mismatch, invalid JSON from the model, schema violation from the model, and Azure service error.
4. THE tests SHALL assert, for each failure scenario in criterion 3, that the API returns an error response indicating the failure category, that no partial Threat_Report is returned, and that the Azure_OpenAI_Client mock is not called for the Image_Validator failures (invalid file type, oversized file, empty file, signature mismatch).
5. THE tests SHALL include property-based tests, each running at least 100 generated examples, for the Threat_Report_Schema round-trip (serialize then parse yields a value equal to the original) and for the Image_Validator size and signature rules (accepts if and only if the size is within the limit, the size is greater than 0 bytes, and the signature matches the declared type).
6. WHEN a pull request is opened or updated, or WHEN a push occurs to any branch other than `main`, THE Repository SHALL run the full test suite through a GitHub Actions workflow without Azure secrets.
7. IF any test fails in the GitHub Actions workflow, THEN THE workflow SHALL finish with a failed status so that the pull request check is reported as failed.
8. WHEN a client sends a GET request to `/health`, THE API SHALL return HTTP status 200 within 500 milliseconds without calling Azure OpenAI.

### Requirement 7: Documentação em pt-BR

**User Story:** Como leitor do repositório, quero uma documentação detalhada em português do Brasil, para que eu entenda, reproduza e aprenda com o projeto.

#### Acceptance Criteria

1. THE Repository SHALL include a `README.md` at the repository root, written in pt-BR, containing one distinct titled section for each of the following topics: objective, architecture, STRIDE methodology, prerequisites, Azure OpenAI setup, installation, execution, example requests and responses, prompt engineering techniques used, project structure, and limitations (11 sections in total).
2. THE README.md SHALL include, in a dedicated titled section, the Human_Review_Notice and an ethical and defensive-use notice stating that the tool is intended only for analysis of systems the user owns or is authorized to assess.
3. THE Repository SHALL include, under a `docs` folder, exactly one pt-BR Markdown file for each of the following topics: architecture decisions, prompt engineering explanation, security considerations, and lessons learned (4 files), each with at least one titled section and referenced by a relative link from the `README.md`.
4. THE Repository SHALL include an `images` folder containing at least one sample architecture diagram image file (PNG, JPG, or SVG) that is the same diagram used as input in the files under the `examples` folder.
5. WHERE screenshots of the running API are available, THE Repository SHALL include at least one screenshot image file in the `images` folder and reference it from the `README.md`.
6. THE Repository SHALL include an `examples` folder containing at least one sample request file and at least one sample response file, where the response file is a valid output of the system for the sample request and both files are referenced from the `README.md`.
7. THE documentation SHALL describe the Azure OpenAI configuration steps using only placeholder values (for example, `<seu-endpoint>`, `<sua-chave>`, `<nome-do-deployment>`) for endpoints, keys, and resource names.
8. IF any file in the Repository contains a real Azure OpenAI endpoint, API key, or resource name, THEN THE Repository SHALL be considered non-compliant with this requirement, and the value SHALL be replaced by a placeholder before publication.
9. THE Repository SHALL include a `LICENSE` file at the repository root containing the full text of a single, named open-source license.

### Requirement 8: Fluxo Git e publicação

**User Story:** Como mantenedor, quero um fluxo Git seguro e a publicação do projeto no GitHub, para que o código seja compartilhado de forma rastreável.

#### Acceptance Criteria

1. WHEN the maintainer publishes the project for the first time, THE Repository SHALL be created as a new public repository under the GitHub account Gtvnv, with the initial commit containing at least one tracked file.
2. WHEN the maintainer creates a commit, THE Repository SHALL include only files that were individually named in the staging command, and the commit SHALL NOT include bulk staging of all changes.
3. IF a file named `.env`, or a file containing credentials, API keys, tokens or private keys, is present in the working tree, THEN THE Repository SHALL exclude it from the commit through an ignore rule, and the commit SHALL contain 0 such files.
4. IF the maintainer is about to commit a file likely to contain secrets (such as `.env`, a credential JSON file or a key file), THEN THE maintainer SHALL flag the file and obtain confirmation before staging it, and the file SHALL remain unstaged until confirmed.
5. WHERE the repository is not a new personal repository under the Gtvnv account (for example a repository of another account, an organization or a third party), THE maintainer SHALL create a work branch whose name uses a prefix of feature/, fix/, hotfix/, chore/, refactor/, docs/ or test/, push it with remote tracking, and integrate changes into the main branch only through a pull request approved by at least 1 human reviewer.
6. IF a change would write directly to the main branch of a repository covered by criterion 5, THEN THE maintainer SHALL refuse the direct write, leave the main branch pointer unchanged, and propose the work branch and pull request path instead.
