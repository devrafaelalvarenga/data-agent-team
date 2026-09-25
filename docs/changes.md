# Changelog

Registro de mudanças relevantes no framework e nos projetos. Ver histórico
completo de commits com `git log` para detalhes granulares.

## 25/09/2026 (5)

- Troca `AneelCsvExtractSpecialist` por `AneelParquetExtractSpecialist`
  (`projects/ai-energy-data-project/extract_impl.py`): fontes ANEEL agora em
  Parquet, não CSV -- schema tipado embutido, carga nativa mais eficiente no
  BigQuery. Converte colunas de data/decimal do parquet para ISO
  string/float (não são JSON-safe por padrão, e `raw_content` precisa
  trafegar via XCom). Adiciona `pyarrow` como dependência.
- `config.yaml`: fontes renomeadas para `aneel_drp_drc_parquet`/
  `aneel_dec_fec_parquet`, resource de DEC/FEC trocado de
  `indicadores-continuidade-coletivos-limite` (só limites regulatórios) para
  `indicadores-continuidade-coletivos-2020-2029.parquet` (série histórica de
  valores medidos) -- decisão do usuário, resolve pendência anterior.

## 25/09/2026 (4)

- Adiciona `core/orchestration/dag_factory.py` (encadeia as 4 Tasks numa DAG
  do Airflow via TaskFlow API, `from airflow.sdk import dag, task` -- API
  confirmada contra a doc oficial, mudou de `airflow.decorators`) e
  `core/orchestration/serialization.py` (serializa Bronze/Silver/EvalResult
  para XCom -- JSON não aceita dataclass nem bytes, por isso base64 explícito
  para `raw_content` binário; sem dependência de `airflow`, com testes reais).
- Monta o scaffold do projeto Astro manualmente (`Dockerfile`,
  `.dockerignore`, `packages.txt`, `requirements.txt`, `dags/`, `include/`,
  `plugins/`, `tests/dags/test_dag_example.py`) -- `astro dev init --force`
  foi bloqueado pelo classificador de segurança do Claude Code por risco de
  sobrescrever `.env`/`README.md`/`.gitignore` já existentes; o scaffold
  equivalente foi inspecionado numa pasta isolada e replicado manualmente,
  sem tocar nesses arquivos. `pyproject.toml` passa a ignorar `tests/dags/`
  no `uv run pytest` (precisa de `airflow`, só roda via `astro dev pytest`).
- Cria `projects/ai-energy-data-project/config.yaml` (real, substitui o
  exemplo ilustrativo) e `dags/ai_energy_data_project.py` (DAG real da
  pipeline `prodist_pdf`, único caminho completo hoje -- as fontes CSV ainda
  não têm `TransformSpecialist`, ver `docs/integrations/apache-airflow-astro.md`
  e `projects/ai-energy-data-project/docs/architecture.md`, ambos criados
  agora).
- `apache-airflow` não é dependência do `uv`: exige constraints rígidas e um
  pacote transitivo (`libcst`) sem wheel prebuilt para esta plataforma
  (confirmado tentando `uv run --with apache-airflow`). Roda só dentro do
  container do Astro Runtime.

## 25/09/2026 (3)

- Adiciona `core/load/base.py`: `LoadGate` genérico (Task 4) -- grava em Gold
  se `EvalResult.passed`, senão gera um `AuditRecord` por `SilverRecord`
  (com `rejected_at` ISO 8601) e grava em Auditoria. 100% determinístico,
  conforme especificado em `docs/ARCHITECTURE.md`.

## 25/09/2026 (2)

- Adiciona `core/harness/base.py` (Harness genérico: amostragem + cálculo de
  nota) e `core/harness/metrics.py` (`faithfulness_to_source`,
  `chunk_size_valid`, `metadata_extracted`), registradas via `@register_metric`.
  Convenção: métricas leem só `SilverRecord.metadata`, nunca a forma de
  `transformed_content` (específica de cada projeto) -- mantém as métricas de
  `core/` genéricas. `faithfulness_to_source` agrega o resultado que o
  orquestrador grava em `metadata["transform_approved"]` a partir do
  `TransformSupervisor.review()` -- não faz uma segunda chamada de LLM.

## 25/09/2026

- Adiciona `core/providers/google_ai_studio.py`: provider Gemini (SDK
  `google-genai`) registrado via `@register_provider("google_ai_studio")`.
  Ver `docs/integrations/google-ai-studio.md`.
- Adiciona `projects/ai-energy-data-project/transform_impl.py`:
  `PdistChunkingTransformSpecialist` (chunking por seção numerada + limpeza
  via LLM) e `PdistFidelityTransformSupervisor` (checagem de fidelidade
  seção a seção via LLM).
- Cria `docs/integrations/` (README índice + `google-ai-studio.md` +
  `aneel-dados-abertos.md`), `docs/roadmap.md` e este `docs/changes.md` --
  documentos obrigatórios pelo `CLAUDE.md` que ainda não existiam.

## 24/09/2026

- Scaffold inicial do framework: `core/contracts.py`, `core/registry.py`,
  `core/extract/base.py`, `core/transform/base.py`.
- `projects/ai-energy-data-project/extract_impl.py`: `AneelCsvExtractSpecialist`
  (CKAN) e `ProdistPdfExtractSpecialist`.
- Migração de `requirements.txt` para `uv` nativo (`pyproject.toml` + `uv.lock`).
- Correção: `gitignore`/`env.example` sem o ponto inicial faziam o Git não
  ignorar nada de fato -- renomeados para `.gitignore`/`.env.example`.
- Primeiro commit e push do repositório.
