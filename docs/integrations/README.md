# Integrações Externas

Índice de todas as integrações com serviços externos documentadas neste
repositório. Ver `CLAUDE.md` para as regras obrigatórias de documentação de
integrações.

| Integração | Usada em | Documento |
|---|---|---|
| Google AI Studio (Gemini) | `core/providers/google_ai_studio.py`, `projects/ai-energy-data-project/transform_impl.py` | [`google-ai-studio.md`](google-ai-studio.md) |
| ANEEL Dados Abertos (CKAN) + PRODIST | `projects/ai-energy-data-project/extract_impl.py` | [`aneel-dados-abertos.md`](aneel-dados-abertos.md) |
| Apache Airflow via Astro CLI | `core/orchestration/dag_factory.py`, `dags/` | [`apache-airflow-astro.md`](apache-airflow-astro.md) |
