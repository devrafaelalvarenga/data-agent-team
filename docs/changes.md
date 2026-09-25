# Changelog

Registro de mudanças relevantes no framework e nos projetos. Ver histórico
completo de commits com `git log` para detalhes granulares.

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
