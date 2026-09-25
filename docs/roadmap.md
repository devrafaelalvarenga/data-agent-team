# Roadmap

Baseado na seção "Roadmap de implementação sugerido" de `docs/ARCHITECTURE.md`.

## Concluído

1. `core/contracts.py` — BronzeRecord, SilverRecord, SupervisorVerdict, EvalResult, AuditRecord
2. `core/registry.py` — `@register_metric` / `@register_provider`
3. `core/extract/base.py` — ExtractSpecialist (ABC) + ExtractSupervisor (schema/completude/freshness, fail-closed)
4. `projects/ai-energy-data-project/extract_impl.py` — as 3 fontes (PRODIST PDF, DRP/DRC, DEC/FEC — Parquet, ver item 18)
5. `core/transform/base.py` — TransformSpecialist (ABC) + TransformSupervisor (ABC)
6. `core/providers/google_ai_studio.py` — provider Gemini registrado (`google_ai_studio`)
7. `projects/ai-energy-data-project/transform_impl.py` — chunking por seção numerada do PRODIST + limpeza/checagem de fidelidade via LLM
8. `core/harness/base.py` + `core/harness/metrics.py` — Harness genérico com amostragem (`random`, outras estratégias levantam `NotImplementedError`) + 3 métricas registradas (`faithfulness_to_source`, `chunk_size_valid`, `metadata_extracted`), todas lendo só `SilverRecord.metadata` (convenção documentada no módulo) para ficarem genéricas entre projetos
9. `core/load/base.py` — LoadGate genérico: grava em Gold se `EvalResult.passed`, senão gera um `AuditRecord` por `SilverRecord` e grava em Auditoria. Sempre determinístico.
10. `core/orchestration/dag_factory.py` + `core/orchestration/serialization.py` — `build_pipeline_dag` encadeia as 4 Tasks numa DAG do Airflow (`from airflow.sdk import dag, task`, API atual do Airflow 3.x). `dag_factory.py` popula `metadata["transform_approved"]` com o veredito do `TransformSupervisor` antes de entregar ao Harness. Serialização Bronze/Silver/EvalResult para XCom extraída em módulo próprio, sem depender de `airflow`, com testes reais.
11. Scaffold do projeto Astro (`Dockerfile`, `.dockerignore`, `packages.txt`, `requirements.txt`, `dags/`, `include/`, `plugins/`, `tests/dags/`) montado manualmente (equivalente a `astro dev init`, sem sobrescrever `.env`/`README.md`/`.gitignore`)
12. `projects/ai-energy-data-project/config.yaml` — real, cobre as 3 fontes (extract) + a pipeline completa de `prodist_pdf` (transform/harness/load)
13. `dags/ai_energy_data_project.py` — DAG real da pipeline `prodist_pdf`, resolvendo `config.yaml` em componentes via `core/registry.py`
14. `projects/ai-energy-data-project/docs/architecture.md` — decisões técnicas específicas do projeto
15. `aneel_drp_drc_csv`/`aneel_dec_fec_csv` → `aneel_drp_drc_parquet`/`aneel_dec_fec_parquet`: `AneelCsvExtractSpecialist` virou `AneelParquetExtractSpecialist` (Parquet em vez de CSV -- schema tipado embutido, carga mais eficiente no BigQuery). DEC/FEC agora usa `indicadores-continuidade-coletivos-2020-2029.parquet` (série histórica de valores medidos), não mais `-limite` (só limites regulatórios)
16. `AneelTabularTransformSpecialist` + `AneelTabularTransformSupervisor` (`transform_impl.py`) — Transform determinístico (sem LLM) para `aneel_drp_drc_parquet`/`aneel_dec_fec_parquet`, decisão documentada em `projects/ai-energy-data-project/docs/architecture.md`. `core/transform/base.py` e `docs/ARCHITECTURE.md` atualizados para deixar explícito que `TransformSupervisor` não precisa ser sempre LLM.

## Em andamento / pendente

17. `aneel_drp_drc_parquet`/`aneel_dec_fec_parquet` têm Extract+Transform, mas ainda sem DAG (Harness/Load precisam ser wireados numa `dags/*.py` como foi feito para `prodist_pdf`)
18. `expected_columns` do Transform das fontes ANEEL está vazio em `config.yaml` -- preencher depois de inspecionar o schema real dos resources Parquet contra dado ao vivo
19. Persistência real (GCS/BigQuery) -- `LoadGate` hoje usa `gold_writer`/`audit_writer` placeholders que só logam
20. Validação real de ponta a ponta: rede real (ANEEL/Google AI Studio) e Airflow real (`astro dev start`/`astro dev pytest`) -- não foi possível no ambiente de desenvolvimento (sandbox sem saída de rede via `requests`; Docker não estava rodando)
