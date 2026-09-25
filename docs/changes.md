# Changelog

Registro de mudanças relevantes no framework e nos projetos. Ver histórico
completo de commits com `git log` para detalhes granulares.

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
