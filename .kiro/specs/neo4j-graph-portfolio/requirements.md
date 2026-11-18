# Requirements Document

## Introduction

Este documento define os requisitos de um repositório GitHub de portfólio que demonstra um projeto de banco de dados em grafos com Neo4j. O domínio escolhido é a **gestão de exposição a vulnerabilidades**: ativos de TI, softwares instalados, vulnerabilidades (CVEs), ameaças e caminhos de ataque. Esse domínio é naturalmente relacional e justifica o uso de grafos, pois perguntas como "quais ativos críticos são alcançáveis a partir de um ativo exposto à internet?" exigem travessias de múltiplos saltos.

O repositório é educacional e autocontido. Usa apenas dados sintéticos e seguros, sem exploits, payloads ou dados reais de organizações. Toda a documentação é escrita em português do Brasil (pt-BR). Nenhum arquivo do projeto referencia plataformas de curso ou bootcamp. O repositório é inspirado nos exemplos oficiais de https://github.com/neo4j-graph-examples.

## Glossary

- **Repositorio**: Repositório Git do projeto, publicado no GitHub.
- **README**: Arquivo `README.md` na raiz do Repositorio, escrito em pt-BR.
- **Neo4j**: Sistema gerenciador de banco de dados em grafos usado no projeto.
- **Neo4j_Browser**: Interface web do Neo4j para executar consultas Cypher e visualizar resultados.
- **Cypher**: Linguagem de consulta do Neo4j.
- **Modelo_de_Grafo**: Definição de rótulos (labels), relacionamentos e propriedades do grafo.
- **Ativo**: Servidor, estação de trabalho, dispositivo de rede ou serviço, representado pelo rótulo `Asset`.
- **Software**: Produto de software instalado em Ativos, representado pelo rótulo `Software`.
- **Vulnerabilidade**: Falha identificada por um CVE, representada pelo rótulo `Vulnerability`.
- **Ameaca**: Grupo ou técnica de ataque fictício ou público de referência, representado pelo rótulo `Threat`.
- **Rede**: Segmento de rede onde Ativos se conectam, representado pelo rótulo `Network`.
- **Caminho_de_Ataque**: Sequência de Ativos conectados que leva de um Ativo exposto a um Ativo crítico.
- **Dataset**: Conjunto de arquivos CSV sintéticos que alimentam o grafo.
- **Scripts_de_Carga**: Arquivos Cypher que criam constraints, índices e carregam o Dataset via `LOAD CSV`.
- **Consultas_de_Negocio**: Consultas Cypher que respondem às perguntas de negócio documentadas.
- **Evidencia_Visual**: Captura de tela do Neo4j_Browser, Bloom ou Explore que comprova o resultado de uma consulta.
- **Imagem_de_Schema**: Imagem do Modelo_de_Grafo, desenhada no Arrows.app ou exportada de `CALL db.schema.visualization()`.
- **Ambiente_Local**: Ambiente de execução do projeto, composto por Neo4j executado via Docker Compose.
- **Aviso_de_Uso_Etico**: Seção que declara o uso exclusivamente educacional e defensivo do projeto.

## Requirements

### Requirement 1: README com contexto e justificativa

**User Story:** Como recrutador ou leitor técnico, quero entender o problema e a motivação do projeto no README, para avaliar rapidamente a relevância do trabalho.

#### Acceptance Criteria

1. THE README SHALL be written entirely in pt-BR, except for code blocks, command names, identifiers and proper names of technologies.
2. THE README SHALL contain a section describing the problem context of vulnerability exposure management, with a text of 100 to 400 words that defines the term "exposição de vulnerabilidades" and names at least one limitation of tracking vulnerabilities in isolation (without relationships between assets, vulnerabilities and attack paths).
3. THE README SHALL contain a section justifying the choice of a graph database over a relational database, citing at least two multi-hop questions (each traversing 3 or more relationships) that the Modelo_de_Grafo answers, where each question is stated in natural language and identifies the node types and relationship types it traverses.
4. THE README SHALL contain a table of contents placed before the first top-level section, with one link for each top-level section, where each link navigates to the matching section heading.
5. THE README SHALL contain a section describing the technology stack, listing each technology with its name and version, including the Neo4j version in the format MAJOR.MINOR (for example, "5.26").
6. THE README SHALL contain the Aviso_de_Uso_Etico as a section with its own heading, positioned before any section that contains execution instructions or commands.
7. IF a link in the table of contents does not match an existing section heading in the README, THEN THE README SHALL be considered non-compliant with criterion 4.

### Requirement 2: Instruções de execução reproduzíveis

**User Story:** Como usuário do repositório, quero instruções claras de execução, para reproduzir o projeto na minha máquina sem ajuda externa.

#### Acceptance Criteria

1. THE README SHALL list the prerequisites needed to run the project, including Docker with a minimum version number, Docker Compose with a minimum version number, and the minimum free disk space and RAM in GB required to run the Ambiente_Local.
2. THE Repositorio SHALL provide a `docker-compose.yml` that starts a Neo4j container with the Dataset files mounted read-only in the Neo4j import directory.
3. THE README SHALL provide numbered step-by-step commands that take a user from `git clone` to a populated graph, where each step lists the exact command to run and the expected outcome of that step.
4. THE README SHALL state the Neo4j_Browser URL, including host and port, and the username and password variable names configured for the Ambiente_Local, with the password value referenced from `.env.example` placeholders instead of a real secret.
5. THE Repositorio SHALL provide a `.env.example` file containing every Neo4j credential variable referenced by `docker-compose.yml`, each with a placeholder value that is not a real credential.
6. THE Repositorio SHALL list the file `.env` in `.gitignore`, so that `git status` does not show a `.env` file as untracked or staged.
7. WHEN the user runs the documented load command on an empty database, THE Scripts_de_Carga SHALL finish with exit code 0, report zero Cypher errors, and complete within 300 seconds.
8. THE README SHALL describe a verification query that returns the count of nodes per label, and a table listing each label with its expected node count.
9. IF the Neo4j container is not reachable, or the load command fails, THEN THE README SHALL provide a troubleshooting section listing at least the following: port already in use, missing `.env` file, and Dataset files not found in the import directory. Each item SHALL state the symptom and the corrective action.
10. WHEN the user runs the documented load command a second time on an already populated database, THE Scripts_de_Carga SHALL leave the node count per label identical to the expected counts in the README, without creating duplicate nodes.

### Requirement 3: Modelo de grafo documentado com imagens

**User Story:** Como leitor, quero ver o modelo do grafo em imagens claras, para compreender rótulos, relacionamentos e propriedades.

#### Acceptance Criteria

1. THE Repositorio SHALL contain at least one Imagem_de_Schema drawn in Arrows.app that shows all 5 labels defined in criterion 7, all relationship types defined in criterion 8, and the properties of each label and relationship type.
2. THE Repositorio SHALL contain one Imagem_de_Schema exported from `CALL db.schema.visualization()` executed against the loaded graph, showing all labels and relationship types present in the database at export time.
3. THE Imagem_de_Schema files SHALL be in PNG or SVG format, with a width of at least 1200 pixels for PNG, so that label names and relationship type names are readable at 100% zoom.
4. THE README SHALL embed each Imagem_de_Schema present in the Repositorio, with alternative text in pt-BR of 1 to 250 characters that names the labels and relationships shown.
5. THE README SHALL contain a table with one row per label, with columns for label name, property name, data type and unique key property, covering 100% of the labels in the Modelo_de_Grafo.
6. THE README SHALL contain a table with one row per relationship type, with columns for relationship type name, source label, target label and properties (or "nenhuma" when the relationship type has no properties), covering 100% of the relationship types in the Modelo_de_Grafo.
7. THE Modelo_de_Grafo SHALL include the labels `Asset`, `Software`, `Vulnerability`, `Threat` and `Network`.
8. THE Modelo_de_Grafo SHALL include one relationship type for each of the following: Software installed on Asset, Asset affected by Vulnerability, Asset connected to Network, Asset able to reach Asset, and Threat exploiting Vulnerability.
9. WHERE an Arrows.app source file is available, THE Repositorio SHALL include the JSON exported from Arrows.app for the diagram, in a file that Arrows.app can re-import without error.
10. IF the labels or relationship types in the schema visualization exported by `CALL db.schema.visualization()` differ from those in the README tables, THEN THE Repositorio SHALL be considered non-compliant until the image or the tables are updated so that both list the same labels and relationship types.

### Requirement 4: Dataset e scripts de carga

**User Story:** Como desenvolvedor, quero um dataset de exemplo e scripts de carga comentados, para entender como os dados entram no grafo.

#### Acceptance Criteria

1. THE Repositorio SHALL contain a Dataset of CSV files encoded in UTF-8 with a header row, with exactly one file per node label (Ativo, Software, Vulnerabilidade, Ameaca, Rede) and exactly one file per relationship type used in the graph model.
2. THE Dataset SHALL contain at least 30 Ativos, 15 Softwares, 25 Vulnerabilidades, 5 Ameacas and 5 Redes, and each node label SHALL have a unique key value per row within its CSV file.
3. THE Dataset SHALL contain only synthetic data, with every IP address within the private ranges 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 or the documentation ranges 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24 defined in RFC 5737.
4. THE Dataset SHALL reference CVE identifiers that match the regular expression `^CVE-[0-9]{4}-[0-9]{4,}$`, with each identifier accompanied by a descriptive text of 1 to 300 characters and a CVSS score between 0.0 and 10.0 with at most one decimal place.
5. THE Dataset SHALL contain relationship rows whose source and target key values all exist in the CSV file of the corresponding node label.
6. WHEN the Scripts_de_Carga start, THE Scripts_de_Carga SHALL create a uniqueness constraint for the key property of each of the 5 node labels, using `IF NOT EXISTS`, before executing any `LOAD CSV` statement.
7. WHEN the Scripts_de_Carga load data, THE Scripts_de_Carga SHALL load each CSV file using `LOAD CSV WITH HEADERS` and write nodes and relationships using the `MERGE` clause.
8. THE Scripts_de_Carga SHALL contain a comment in pt-BR immediately before each step (constraint creation, node load and relationship load) describing the purpose of that step.
9. WHEN the Scripts_de_Carga run a second consecutive time on the same database, THE Scripts_de_Carga SHALL complete without error and leave the total count of nodes per label and relationships per type identical to the counts after the first run.
10. IF a CSV row has an empty or missing key value, THEN THE Scripts_de_Carga SHALL skip that row, SHALL NOT create any node or relationship from it, and SHALL continue processing the remaining rows.
11. IF a relationship CSV row references a source or target key that does not exist as a node, THEN THE Scripts_de_Carga SHALL NOT create the relationship nor create a new node for the missing key.
12. THE Repositorio SHALL contain a data dictionary document that, for each CSV file, lists the file name, the node label or relationship type it represents, and for each column its name, data type, whether it is required, and an example value.

### Requirement 5: Consultas de negócio

**User Story:** Como analista de segurança, quero perguntas de negócio respondidas por consultas Cypher, para ver o valor prático do grafo.

#### Acceptance Criteria

1. THE README SHALL list between 8 and 15 business questions, each mapped one-to-one to a Consulta_de_Negocio.
2. THE Repositorio SHALL contain each Consulta_de_Negocio as one commented Cypher file containing three parts: the business question, the query, and an interpretation of the result of at most 500 characters.
3. THE Consultas_de_Negocio SHALL include a query returning the Ativos ordered by descending count of Vulnerabilidades with CVSS score greater than or equal to 9.0, limited to the top 10 Ativos, with Ativo identifier and count in each row.
4. THE Consultas_de_Negocio SHALL include a variable-length path query returning Caminhos_de_Ataque from Ativos with internet exposure to Ativos marked as critical, with path length between 1 and 5 hops inclusive, limited to 25 paths.
5. THE Consultas_de_Negocio SHALL include a query returning the Software ordered by descending count of distinct Ativos affected through its Vulnerabilidades, limited to the top 10 Software, with Software name and count in each row.
6. THE Consultas_de_Negocio SHALL include a query returning the distinct Ameacas that reach Ativos marked as critical through Vulnerabilidades flagged as exploitable, with Ameaca name and count of critical Ativos reached in each row.
7. THE Consultas_de_Negocio SHALL include a query returning the Redes ordered by descending sum of the CVSS scores of the Vulnerabilidades of their Ativos, limited to the top 10 Redes, with Rede identifier and sum in each row.
8. THE Consultas_de_Negocio SHALL include at least one query using `shortestPath` or a graph algorithm, returning the shortest path between one internet-exposed Ativo and one critical Ativo, with path length in hops.
9. WHEN a Consulta_de_Negocio runs on the loaded Dataset, THE Neo4j SHALL return at least one row and finish within 10 seconds.
10. THE README SHALL document the expected result of each Consulta_de_Negocio as a table with at least the first 3 rows returned, or as an Evidencia_Visual of the result.
11. IF a Consulta_de_Negocio returns zero rows on the loaded Dataset, THEN THE Repositorio SHALL mark that query as failed in its verification step and report the name of the failing query.

### Requirement 6: Evidências visuais

**User Story:** Como avaliador, quero evidências visuais dos resultados, para confirmar que os insights foram de fato obtidos no grafo.

#### Acceptance Criteria

1. THE Repositorio SHALL contain at least one Evidencia_Visual for each Consulta_de_Negocio listed in the README, with each Evidencia_Visual referenced by exactly one Consulta_de_Negocio.
2. THE Repositorio SHALL store Evidencia_Visual files in the `docs/images` directory, in PNG or JPG format, with file names in kebab-case that include the identifier or name of the corresponding Consulta_de_Negocio, each file not exceeding 5 MB.
3. THE README SHALL embed each Evidencia_Visual immediately after the Cypher code block of its corresponding Consulta_de_Negocio, with alternative text in pt-BR of 10 to 150 characters describing the query and the result shown.
4. THE Evidencia_Visual SHALL show, in a single image, the complete executed Cypher query text and the returned result in the Neo4j_Browser, Bloom or Explore, with the query text legible at 100% zoom.
5. THE Evidencia_Visual of Caminhos_de_Ataque SHALL show a graph visualization containing at least 2 nodes and 1 relationship, with node labels or captions visible.
6. THE Evidencia_Visual files SHALL contain no credentials, connection strings, personal data or real organization data.
7. IF a Consulta_de_Negocio listed in the README has no corresponding Evidencia_Visual file in `docs/images`, THEN THE Repositorio SHALL be considered non-compliant with this requirement, and the README SHALL NOT contain an image reference pointing to a nonexistent file.

### Requirement 7: Troubleshooting

**User Story:** Como usuário que encontrou problemas, quero uma seção de troubleshooting, para resolver dificuldades comuns sem abrir uma issue.

#### Acceptance Criteria

1. THE README SHALL contain a section titled "Troubleshooting" written in pt-BR, listed in the README table of contents.
2. THE troubleshooting section SHALL document between 5 and 15 difficulties found during development, and each difficulty SHALL have three labeled fields: sintoma, causa and solução.
3. THE troubleshooting section SHALL include, for each difficulty, a solução containing at least one command or one configuration change that the user can execute or apply as written.
4. THE troubleshooting section SHALL include an entry for permission errors on the Neo4j import directory or file path errors in `LOAD CSV`, whose sintoma identifies the error observed when the CSV file is not found or not readable.
5. THE troubleshooting section SHALL include an entry for Neo4j authentication failures or initial password errors, whose solução describes how to set or reset the password and where to update the credentials used by the project.
6. THE troubleshooting section SHALL include an entry for Docker port conflicts on ports 7474 and 7687, whose solução describes how to identify the process using each port and how to free or remap each port.
7. THE troubleshooting section SHALL include an entry for CSV encoding or line-ending issues on Windows (such as BOM or CRLF), whose solução describes how to convert the file to UTF-8 with LF line endings.
8. THE troubleshooting section SHALL include an entry for memory or timeout problems on variable-length path queries, whose solução describes at least two mitigations: limiting the maximum path length in the query and adjusting the Neo4j memory or transaction timeout setting.
9. WHEN a user follows the solução of a documented difficulty on a clean installation that reproduces the sintoma, THE troubleshooting section SHALL lead to the sintoma being resolved, as verified by a manual check of each entry before release.

### Requirement 8: Organização e qualidade do repositório

**User Story:** Como mantenedor, quero que o repositório seja organizado e limpo, para que ele tenha aparência profissional e seja fácil de navegar.

#### Acceptance Criteria

1. THE Repositorio SHALL organize files into the directories `data`, `cypher`, `docs` and `docs/images`, and SHALL contain no other top-level directory except `.git` and `.kiro`.
2. THE Repositorio SHALL contain a `LICENSE` file in the repository root whose text is the full, unmodified text of one license approved by the Open Source Initiative (OSI), with the copyright holder name and a four-digit year filled in.
3. THE Repositorio SHALL contain a `.gitignore` file in the repository root with at least one pattern each for environment files (`.env`), Neo4j data volumes, and operating system artifacts (`.DS_Store` and `Thumbs.db`).
4. THE Repositorio SHALL contain no occurrence of the terms "bootcamp", "curso", "course" or "plataforma de aprendizado" (case-insensitive) in any tracked file name, file content or commit message.
5. THE README SHALL contain a section titled with the word "Créditos" or "Credits" that includes the link https://github.com/neo4j-graph-examples and a sentence stating that the project was inspired by it.
6. THE README SHALL contain a section titled "Estrutura do projeto" or "Project structure" that shows a directory tree listing `data`, `cypher`, `docs` and `docs/images`, with one description of at most 100 characters on the same line as each directory.
7. THE Repositorio SHALL contain a `CONTRIBUTING.md` file, or a README section titled "Contribuindo" or "Contributing", stating that every contribution must be made on a separate branch and submitted through a Pull Request, and that direct commits to `main` are not accepted.
8. THE README SHALL contain a section titled "Próximos passos" or "Next steps" that lists at least three and at most ten distinct possible improvements, each as a separate list item.
9. IF a tracked file contains a term listed in criterion 4, THEN THE Repositorio SHALL be considered non-compliant until the term is removed from that file.
10. IF a required file or section from criteria 2, 3, 5, 6, 7 or 8 is missing, THEN THE Repositorio SHALL be considered non-compliant with this requirement.

### Requirement 9: Controle de versão seguro

**User Story:** Como mantenedor, quero um controle de versão seguro, para que as mudanças sigam o fluxo de branches e Pull Requests.

#### Acceptance Criteria

1. WHEN a maintainer starts a change, THE Repositorio SHALL require the change to be made on a work branch created from the current base branch, named in kebab-case with a length of 3 to 60 characters and one of the prefixes `feature/`, `fix/`, `chore/`, `docs/` or `test/`.
2. IF the remote of the Repositorio is not a repository under the account `Gtvnv` on `github.com`, THEN THE Repositorio SHALL reject any direct commit, push, merge, rebase or reset that changes the `main` branch, and SHALL accept changes to `main` only through a Pull Request approved by at least 1 human reviewer other than the author.
3. WHERE the remote of the Repositorio is a new personal repository under the account `Gtvnv` on `github.com`, THE maintainer SHALL be allowed to commit and push directly to `main`, and force push, hard reset and history rewriting on `main` SHALL remain prohibited unless explicitly requested.
4. IF a staged file is a `.env` file, a credential file or a private key (for example `.env`, `*.pem`, `*.key`, or a JSON file containing credentials), THEN THE Repositorio SHALL block the commit, SHALL leave the working tree files unchanged, and SHALL report an error that names each blocked file.
5. WHEN a maintainer opens a Pull Request, THE Repositorio SHALL require a title of at most 72 characters and a description that states the change summary, what was tested and what remains pending.

### Requirement 10: Validação automatizada dos artefatos

**User Story:** Como mantenedor, quero validação automatizada dos artefatos, para garantir que dataset, scripts e documentação permaneçam consistentes.

#### Acceptance Criteria

1. THE Repositorio SHALL provide a single validation script that runs all checks in criteria 2 to 6 in one execution, without requiring user input or network access.
2. WHEN the validation script runs, THE validation script SHALL verify that every CSV file referenced by the Scripts_de_Carga exists in the `data` directory.
3. WHEN the validation script runs, THE validation script SHALL verify that the header row of every CSV file in the `data` directory contains all column names listed for that file in the data dictionary, with exact, case-sensitive matching.
4. WHEN the validation script runs, THE validation script SHALL verify that every row of every relationship CSV file references source and target node keys that each match exactly one key in the corresponding node CSV file.
5. WHEN the validation script runs, THE validation script SHALL verify that no text file in the Repositorio contains the name of a bootcamp or course platform from a deny list of names, with case-insensitive matching.
6. WHEN the validation script runs, THE validation script SHALL verify that every image path referenced in the README resolves to an existing file in the Repositorio.
7. IF the validation script finds a violation, THEN THE validation script SHALL continue running the remaining checks, print for each violation the file name, the line number (when applicable) and a description of the violation, and exit with a non-zero code.
8. WHEN the validation script finds no violations, THE validation script SHALL print a message indicating success and exit with code 0.
9. IF a file required by a check is missing, unreadable, or not valid CSV, THEN THE validation script SHALL report that file as a violation, skip the dependent checks for that file, and exit with a non-zero code.
