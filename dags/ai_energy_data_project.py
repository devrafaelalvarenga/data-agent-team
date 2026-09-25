"""DAG do ai-energy-data-project: pipeline completa (Extract -> Transform ->
Harness -> Load) da fonte prodist_pdf.

Só roda dentro do container do Astro (precisa de `airflow` instalado -- ver
core/orchestration/dag_factory.py). Este arquivo é o único lugar que conhece
a pasta kebab-case do projeto e resolve `config.yaml` em componentes reais;
`core/orchestration/dag_factory.py` continua 100% genérico.

aneel_drp_drc_csv e aneel_dec_fec_csv ainda não têm DAG: falta decidir e
implementar o TransformSpecialist delas -- ver
projects/ai-energy-data-project/docs/architecture.md.
"""

import importlib.util
import logging
import pathlib

import yaml

# side effect: os imports abaixo populam METRIC_REGISTRY/PROVIDER_REGISTRY
# (@register_metric/@register_provider rodam ao importar o módulo) -- sem
# eles, PROVIDER_REGISTRY["google_ai_studio"] e METRIC_REGISTRY[...] abaixo
# dariam KeyError. Nenhum nome deles é referenciado diretamente aqui.
import core.harness.metrics
import core.providers.google_ai_studio  # noqa: F401
from core.contracts import AuditRecord, SilverRecord
from core.extract.base import ExtractSupervisor
from core.harness.base import Harness
from core.load.base import LoadGate
from core.orchestration.dag_factory import build_pipeline_dag
from core.registry import METRIC_REGISTRY, PROVIDER_REGISTRY

_PROJECT_DIR = (
    pathlib.Path(__file__).resolve().parent.parent
    / "projects"
    / "ai-energy-data-project"
)

_CONFIG = yaml.safe_load((_PROJECT_DIR / "config.yaml").read_text())

# config.yaml declara tipos como string (YAML não tem um tipo "type") --
# ExtractSupervisor.schema_rules precisa de objetos `type` de verdade.
_TYPE_NAMES: dict[str, type] = {"str": str, "int": int, "float": float, "bool": bool}


def _resolve_schema_rules(raw: dict[str, str]) -> dict[str, type]:
    return {field: _TYPE_NAMES[type_name] for field, type_name in raw.items()}


def _load_project_module(name: str):
    """A pasta do projeto é kebab-case -- não é um pacote Python válido, então
    o módulo é carregado por caminho. Ver docstring de extract_impl.py."""
    spec = importlib.util.spec_from_file_location(name, _PROJECT_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log_gold_writer(records: list[SilverRecord]) -> None:
    # TODO: substituir por gravação real em BigQuery (config["load"]["prodist_pdf"]["gold_destination"]).
    logging.getLogger("ai_energy_data_project").info(
        "GOLD (placeholder, não persistido): %d registro(s)", len(records)
    )


def _log_audit_writer(records: list[AuditRecord]) -> None:
    # TODO: substituir por gravação real em BigQuery (config["load"]["prodist_pdf"]["audit_destination"]).
    logging.getLogger("ai_energy_data_project").warning(
        "AUDITORIA (placeholder, não persistido): %d registro(s) reprovado(s)",
        len(records),
    )


def _build_prodist_dag():
    extract_impl = _load_project_module("extract_impl")
    transform_impl = _load_project_module("transform_impl")

    prodist_config = _CONFIG["extract"]["prodist_pdf"]
    transform_config = _CONFIG["transform"]["prodist_pdf"]
    harness_config = _CONFIG["harness"]["prodist_pdf"]

    extract_specialist = extract_impl.ProdistPdfExtractSpecialist(
        source_name="prodist_pdf", url=prodist_config["url"]
    )
    extract_supervisor = ExtractSupervisor(
        schema_rules=_resolve_schema_rules(
            prodist_config["supervisor"]["schema_rules"]
        ),
        completeness_min_ratio=prodist_config["supervisor"]["completeness_min_ratio"],
        freshness_max_hours=prodist_config["supervisor"]["freshness_max_hours"],
    )

    build_llm_client = PROVIDER_REGISTRY[transform_config["llm_provider"]]
    generate = build_llm_client(model=transform_config["llm_model"])

    transform_specialist = transform_impl.PdistChunkingTransformSpecialist(
        source_name="prodist_pdf", generate=generate
    )
    transform_supervisor = transform_impl.PdistFidelityTransformSupervisor(
        generate=generate
    )

    harness = Harness(
        metrics={name: METRIC_REGISTRY[name] for name in harness_config["metrics"]},
        threshold=harness_config["threshold"],
        sample_size=harness_config["sample_size"],
        sample_strategy=harness_config["sample_strategy"],
    )
    load_gate = LoadGate(gold_writer=_log_gold_writer, audit_writer=_log_audit_writer)

    return build_pipeline_dag(
        dag_id="ai_energy_prodist_pipeline",
        extract_specialist=extract_specialist,
        extract_supervisor=extract_supervisor,
        transform_specialist=transform_specialist,
        transform_supervisor=transform_supervisor,
        harness=harness,
        load_gate=load_gate,
        schedule="@monthly",  # PRODIST muda raramente, ver freshness_max_hours acima
        tags=["data-agent-team", "ai-energy-data-project"],
    )


ai_energy_prodist_pipeline = _build_prodist_dag()
