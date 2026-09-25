# Integração: Apache Airflow via Astro CLI

## O que é

Orquestração das DAGs do framework. Roda em um container Docker gerenciado
pelo Astro CLI (`astro dev start`/`astro dev stop`) -- não em um `apache-airflow`
instalado no venv do `uv`.

## Por que não é uma dependência do `uv`

`apache-airflow` exige um arquivo de constraints rígido por versão de Python
(ver https://airflow.apache.org/docs/apache-airflow/stable/installation/dependencies.html)
e um dos seus pacotes transitivos (`libcst`) não tem wheel prebuilt para esta
plataforma, exigindo compilador Rust -- tentado e confirmado durante o
desenvolvimento (`uv run --with apache-airflow==3.0.6 python -c "import airflow"`
falhou por isso). Por design, o Astro Runtime já traz Airflow pinado dentro
da imagem Docker; instalar de novo no host é desnecessário e arriscado
(conflito de dependências com `google-genai`, `google-cloud-*`, etc.).

**Consequência:** `core/orchestration/dag_factory.py` e `dags/*.py` importam
`airflow`/`from airflow.sdk import dag, task` e só são importáveis dentro do
container do Astro. `uv run pytest tests/` ignora `tests/dags/`
(configurado em `pyproject.toml`) pelo mesmo motivo. A lógica de
serialização usada pela DAG (`core/orchestration/serialization.py`) foi
deliberadamente extraída para não depender de `airflow` e ter cobertura de
teste real no host.

## SDK e docs oficiais

- Docs: https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html
- Import atual (Airflow 3.x): `from airflow.sdk import dag, task` -- mudou de
  `airflow.decorators` nas versões anteriores. Confirmado no README oficial
  de https://github.com/apache/airflow (verificado durante o desenvolvimento,
  não assumido de memória).
- Astro CLI: https://www.astronomer.io/docs/astro/cli/overview

## Estrutura do projeto Astro

Criada manualmente (não via `astro dev init --force`, que seria destrutivo
numa pasta não-vazia -- ver nota abaixo) espelhando exatamente o que
`astro dev init` gera, sem sobrescrever `.env`/`README.md`/`.gitignore`
já existentes:

- `Dockerfile`, `.dockerignore`, `packages.txt`, `requirements.txt` (deps
  Python do container -- mantido manualmente em sincronia com
  `[project.dependencies]` do `pyproject.toml`, ver comentário no arquivo)
- `dags/` -- DAGs do Airflow. `dags/ai_energy_data_project.py` resolve o
  `config.yaml` do projeto em componentes reais e chama
  `core.orchestration.dag_factory.build_pipeline_dag`
- `include/`, `plugins/` -- vazios, `.gitkeep`
- `tests/dags/test_dag_example.py` -- checagem de integridade das DAGs
  (import sem erro, tags, retries >= 2); roda via `astro dev pytest`, nunca
  via `uv run pytest`

> **Nota:** o comando `astro dev init` foi bloqueado pelo classificador de
> segurança do Claude Code (risco de sobrescrever arquivos existentes numa
> pasta não vazia). O scaffold acima foi montado manualmente, arquivo por
> arquivo, inspecionando primeiro a saída de `astro dev init` numa pasta
> isolada.

## Comandos

- Subir ambiente local: `astro dev start` (requer Docker rodando)
- Parar: `astro dev stop`
- Rodar os testes de `tests/dags/` dentro do container: `astro dev pytest`
- UI do Airflow: http://localhost:8080/ depois de `astro dev start`

## Limitações conhecidas

- Não validado ponta a ponta neste ambiente de desenvolvimento: Docker não
  estava rodando durante a implementação. Primeira validação real: rodar
  `astro dev start` e conferir a DAG `ai_energy_prodist_pipeline` na UI.
- XCom (backend padrão) só serializa JSON -- por isso
  `core/orchestration/serialization.py` converte `BronzeRecord`/`SilverRecord`/
  `EvalResult` em dict antes de cada task retornar, com base64 explícito para
  `raw_content` quando é `bytes` (PDF). PDFs grandes podem estourar o limite
  de tamanho do XCom no backend padrão -- se isso acontecer, a solução é um
  XCom backend customizado apontando para o `bronze_destination` (Cloud
  Storage) em vez de passar o conteúdo inteiro pelo XCom (fora do escopo
  atual).
