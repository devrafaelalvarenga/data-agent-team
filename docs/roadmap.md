# Roadmap

Baseado na seção "Roadmap de implementação sugerido" de `docs/ARCHITECTURE.md`.

## Concluído

1. `core/contracts.py` — BronzeRecord, SilverRecord, SupervisorVerdict, EvalResult, AuditRecord
2. `core/registry.py` — `@register_metric` / `@register_provider`
3. `core/extract/base.py` — ExtractSpecialist (ABC) + ExtractSupervisor (schema/completude/freshness, fail-closed)
4. `projects/ai-energy-data-project/extract_impl.py` — as 3 fontes (PRODIST PDF, DRP/DRC CSV, DEC/FEC CSV)
5. `core/transform/base.py` — TransformSpecialist (ABC) + TransformSupervisor (ABC)
6. `core/providers/google_ai_studio.py` — provider Gemini registrado (`google_ai_studio`)
7. `projects/ai-energy-data-project/transform_impl.py` — chunking por seção numerada do PRODIST + limpeza/checagem de fidelidade via LLM

## Em andamento / pendente

8. `core/harness/base.py` + `core/harness/metrics.py` — Harness genérico com amostragem + métricas registradas (faithfulness, chunk_size_valid, metadata_extracted)
9. `core/load/base.py` — LoadGate (gold/auditoria)
10. `core/orchestration/dag_factory.py` — gera DAG do Airflow a partir do `config.yaml`, resolvendo o registry
11. Testes de integração cobrindo o caminho real (rede) para ANEEL e Google AI Studio — não foi possível no ambiente de desenvolvimento (sandbox sem saída de rede via `requests`)
12. `projects/ai-energy-data-project/config.yaml` — ainda não existe como arquivo real, só como exemplo ilustrativo em `docs/ARCHITECTURE.md`
13. `projects/ai-energy-data-project/docs/architecture.md` — decisões técnicas específicas do projeto (ex.: qual resource usar para DEC/FEC)
