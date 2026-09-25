# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
> Este arquivo é o ponto de entrada da IA para este repositório.
> Ele funciona como um índice: não contém detalhes longos — aponta para os documentos certos.
> Toda instrução longa ou técnica vive em docs/. Este arquivo deve permanecer enxuto.
>
> **Este é o único `CLAUDE.md` do repositório.** Governa o framework (`core/`) e todos os
> projetos dentro de `projects/`. Não criar `CLAUDE.md` por projeto.

## 🗂️ Índice de Documentos Obrigatórios

> A IA deve ler todos os arquivos abaixo antes de executar qualquer tarefa.

| Arquivo | Descrição | Atualizado em |
|---|---|---|
| `docs/ARCHITECTURE.md` | Arquitetura do time de agentes: Tasks 1-4, contratos, registry, config.yaml | 25/09/2026 |
| `docs/roadmap.md` | Tarefas pendentes, em andamento e concluídas | 25/09/2026 |
| `docs/changes.md` | Changelog de todas as alterações relevantes | 25/09/2026 |
| `docs/integrations/README.md` | Índice de todas as integrações externas documentadas | 25/09/2026 |
| `projects/<nome>/docs/architecture.md` | Decisões técnicas específicas de cada projeto (um por projeto) | 25/09/2026 (ai-energy-data-project) |

> Regra: toda vez que um arquivo acima for alterado, atualizar imediatamente o campo "Atualizado em" com a data (ex: `24/09/2026`). Ao final de cada sessão, checar se algum arquivo do índice foi modificado e confirmar que o timestamp reflete isso.

-----

## 🏗️ Arquitetura: Time de Agentes de Engenharia de Dados

> Visão resumida — o detalhamento completo (contratos, código-base, config.yaml) vive em `docs/ARCHITECTURE.md`. Ler esse arquivo integralmente antes de implementar qualquer parte do pipeline.

Este repositório é um **framework reutilizável de agentes especializados** para pipelines de dados, estruturado em camadas medallion (bronze/silver/gold):

| Task | Especialista | Supervisor | É LLM? | Saída |
|---|---|---|---|---|
| 1 — Extract | Lê dados brutos da fonte | Valida schema/completude/freshness (limiares no `config.yaml`) | ❌ Não | Bronze |
| 2 — Transform | Processa/transforma o dado bruto | Avalia fidelidade e qualidade semântica | ✅ Sim | Silver |
| 3 — Harness | Amostra o silver, roda métricas de eval, calcula nota | — | Parcial | decide destino |
| 4 — Load | Se nota ≥ threshold → Gold. Se não → Auditoria | Checagem numérica do threshold | ❌ Não | Gold ou Auditoria |

**Regra não-negociável:** LLM só onde há julgamento semântico real (Task 2 e parte da Task 3). Tasks 1 e 4 são sempre determinísticas — nunca implementar como agente LLM.

**Separação estrutural:**
- `core/` — genérico, reutilizável entre qualquer projeto. Só muda quando um segundo projeto real expõe necessidade de generalizar algo.
- `projects/<nome>/` — implementação específica de cada caso de uso. Toda nova implementação vive aqui, nunca em `core/`.

O primeiro projeto é `projects/ai-energy-data-project/` (qualidade de energia elétrica — PRODIST + DRP/DRC + DEC/FEC, dados da ANEEL).

-----

## 🛠️ Stack e Ambiente

- **Linguagem:** Python 3.12
- **Gerenciador de pacotes:** uv
- **Orquestração:** Apache Airflow via Astro CLI (ambiente local containerizado), DAGs geradas por `core/orchestration/dag_factory.py` a partir do `config.yaml` de cada projeto
- **Vector DB:** Chroma (local)
- **Cloud:** GCP (custo zero — apenas serviços "Always Free")
  - Cloud Storage: blobs (ex: PDFs de fontes normativas)
  - BigQuery: dados tabulares em todas as camadas (bronze/silver/gold/auditoria)
  - Google AI Studio (não Vertex AI): geração via Gemini, cota gratuita diária
- **Rodar testes (host):** `uv run pytest tests/ -v` — ignora `tests/dags/` (precisa de `airflow`, ver `docs/integrations/apache-airflow-astro.md`)
- **Lint/format:** `uv run ruff check . --fix && uv run ruff format .`
- **Subir ambiente localmente:** `astro dev start` (requer Docker)
- **Parar ambiente:** `astro dev stop`
- **Testar DAGs (dentro do container):** `astro dev pytest`

-----

## 🧠 Como a IA deve se comunicar

- Sou Data Engenheiro em transição para AI Data Engineering — **não preciso de explicação de conceitos básicos** de programação, SQL, Python ou pipelines de dados tradicionais (ETL, orquestração, warehousing).
- **Explicar em detalhe apenas conceitos específicos do universo de IA/LLM** ainda não dominados: embeddings, estratégias de chunking, vector DBs, RAG, LLMOps, arquitetura multi-agente.
- Ir direto ao ponto: priorizar objetividade e justificativa técnica das decisões em vez de explicações longas.
- Quando sugerir uma abordagem técnica, expor brevemente o trade-off (por que essa opção e não outra).
- Responder sempre em Português do Brasil.

-----

## 📋 Regras Obrigatórias

### Arquitetura de agentes

- [ ] Nunca implementar Task 1 (Extract) ou Task 4 (Load) como agente LLM — são determinísticas por design
- [ ] Toda nova implementação de projeto vive em `projects/<nome>/`, nunca em `core/`
- [ ] Toda métrica do Harness deve ser testável isoladamente e registrada via `@register_metric` — nunca referenciada por string sem estar no `core/registry.py`
- [ ] Todo LLM provider deve ser registrado via `@register_provider` antes de ser referenciado em `config.yaml`

### Documentação

- [ ] Toda alteração na estrutura de tabelas, contratos (`core/contracts.py`) ou fluxo de dados → atualizar `docs/ARCHITECTURE.md`
- [ ] Toda decisão técnica específica de um projeto (chunking, thresholds, escolha de fonte) → documentar em `projects/<nome>/docs/architecture.md`
- [ ] Toda etapa concluída ou iniciada → atualizar `docs/roadmap.md`
- [ ] Toda mudança relevante → registrar em `docs/changes.md` com data e descrição
- [ ] Todo novo documento criado → referenciar no índice deste arquivo com a data

### Código

- [ ] Proibido hardcode de credenciais, chaves de API ou strings de conexão — sempre via `.env`
- [ ] Proibido hardcode de paths, thresholds, nomes de tabela/dataset ou destinos de camada — sempre via `config.yaml` do projeto
- [ ] Tudo precisa ser documentado — funções, componentes, lógicas complexas e decisões de arquitetura
- [ ] Nomenclatura de buckets, datasets, tabelas e arquivos sempre em inglês, `snake_case` (dataset/tabela) ou `kebab-case` (bucket)

### Integrações

- [ ] Toda integração com serviço externo deve ser pesquisada na documentação oficial antes de ser implementada
- [ ] Toda integração deve ser documentada dentro de `docs/integrations/` com um arquivo próprio
- [ ] O arquivo `docs/integrations/README.md` deve ser atualizado com o índice de integrações

### Ambiente e Infraestrutura

- [ ] Criar e manter o arquivo `.env` com todas as chaves necessárias já estruturadas e comentadas, deixando os valores em branco para preenchimento manual
- [ ] Nunca commitar `.env` preenchido — garantir que está no `.gitignore`
- [ ] **Restrição de custo:** usar exclusivamente serviços do GCP dentro do tier "Always Free". Antes de sugerir qualquer novo serviço GCP, validar explicitamente se ele tem tier gratuito permanente — nunca assumir
- [ ] Nunca sugerir Cloud Composer, Cloud SQL ou instâncias sempre ativas (cobram continuamente, sem tier gratuito real)

-----

## 🧪 Padrão de Testes

> Nível de exigência proporcional ao contexto — código de produção precisa de rigor, experimentação não.

- **`core/`:** cobertura obrigatória — é o framework reutilizável, erro aqui propaga para todos os projetos
- **`projects/<nome>/` (implementações):** cobertura obrigatória para specialists, supervisors e métricas customizadas
- **`notebooks/` (experimentação):** isento de teste formal
- **Integrações externas (vector DB, APIs de embedding, GCP):** teste de integração cobrindo o caminho feliz + pelo menos 1 caso de falha (timeout, resposta vazia, rate limit)
- Casos críticos ou com lógica complexa → sempre testar, independente da pasta

-----

## Setup

Todos os comandos devem ser executados na raiz do repositório (`data-agent-team/`).

### Bootstrap inicial (primeira vez)

```bash
mkdir -p data-agent-team/{core,docs,tests/core,tests/projects,projects/ai-energy-data-project}
cd data-agent-team
git init
git branch -M main

# pastas vazias não são versionadas pelo Git por padrão -- .gitkeep garante que apareçam
touch core/.gitkeep projects/ai-energy-data-project/.gitkeep

# criar o .env real a partir do exemplo (nunca commitar o .env preenchido)
cp .env.example .env

# instala as dependências do pyproject.toml/uv.lock em .venv/
uv sync
```

O `.gitignore` da raiz já cobre `.env`, artefatos de Python/uv, dados temporários (`data/tmp/`, `data/raw/`), estado local do Astro CLI e de notebooks — conferir que está presente antes do primeiro commit.

### Primeiro commit

```bash
git add .
git commit -m "docs: arquitetura inicial do framework de agentes de engenharia de dados"
```