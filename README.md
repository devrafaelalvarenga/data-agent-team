# data-agent-team

Reusable multi-agent framework for data engineering pipelines. Specialist + supervisor agents per ETL stage (Extract, Transform, Harness, Load), medallion architecture (bronze/silver/gold), and an LLM-as-judge quality gate that routes data to production or audit based on configurable eval metrics.

## Architecture at a glance

Each pipeline stage is handled by a **specialist agent** (executes the task) and a **supervisor** (validates the result before releasing it to the next stage). LLM agents are used only where semantic judgment is genuinely required — extraction and loading are always deterministic.

| Task | Specialist | Supervisor | LLM? | Output layer |
|---|---|---|---|---|
| 1 — Extract | Reads raw data from source | Validates schema, completeness, freshness | ❌ No | Bronze |
| 2 — Transform | Processes/transforms raw data | Evaluates fidelity and semantic quality | ✅ Yes | Silver |
| 3 — Harness | Samples Task 2 output, runs configured eval metrics | — | Partial | decides destination |
| 4 — Load | Score ≥ threshold → Gold. Below → Audit table | Numeric threshold check | ❌ No | Gold or Audit |

Full details — contracts, base classes, the registry pattern, and the `config.yaml` spec — are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository structure

```
data-agent-team/
├── core/           # reusable framework — specialists, supervisors, harness, registry
├── projects/       # one subfolder per use case, each with its own config.yaml
├── docs/           # framework-level architecture and process docs
└── tests/
```

Each project under `projects/<name>/` has its own README/architecture doc describing its specific data sources and decisions — this file covers the framework only.

## Getting started

```bash
git clone <repo-url>
cd data-agent-team
cp .env.example .env   # fill in your own credentials, never commit this file
uv sync
```

See `docs/ARCHITECTURE.md` for the full implementation roadmap.

## Status

🚧 Early stage — core contracts and the first project implementation (`projects/ai-energy-data-project/`) are in progress.

## Stack

Python 3.12 · uv · Apache Airflow (Astro CLI) · Chroma · Google Cloud Platform (Cloud Storage, BigQuery, Google AI Studio) — cost kept within GCP's Always Free tier.
