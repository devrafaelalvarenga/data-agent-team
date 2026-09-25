"""Monta a DAG do Airflow para as 4 Tasks a partir de componentes já
instanciados (specialists/supervisors/harness/load gate resolvidos pelo
arquivo de DAG do projeto a partir do seu config.yaml -- ver
`dags/ai_energy_data_project.py`). Ver docs/ARCHITECTURE.md, seção "As 4
Tasks", e docs/integrations/apache-airflow-astro.md.

Requer `airflow` instalado -- só é importável dentro do container do Astro
Runtime, nunca no host (uv não gerencia `apache-airflow`: o pacote exige um
arquivo de constraints rígido e não resolve de forma limpa junto com as
outras dependências deste projeto). Por isso este módulo não tem teste que
importe `airflow` de verdade; a lógica de serialização que ele usa
(`core/orchestration/serialization.py`) é testada isoladamente, sem
depender de `airflow`. Validação real: `astro dev start` + UI do Airflow, ou
`astro dev pytest` (roda dentro do container).

Convenção do Harness (ver core/harness/metrics.py): este módulo é quem
grava `SilverRecord.metadata["transform_approved"]` com o veredito do
TransformSupervisor antes de entregar o registro ao Harness.
"""

from typing import Any

from airflow.sdk import dag, task

from core.extract.base import ExtractSpecialist, ExtractSupervisor
from core.harness.base import Harness
from core.load.base import LoadGate
from core.orchestration.serialization import (
    deserialize_bronze,
    deserialize_eval_result,
    deserialize_silver,
    serialize_bronze,
    serialize_eval_result,
    serialize_silver,
)
from core.transform.base import TransformSpecialist, TransformSupervisor


def build_pipeline_dag(
    *,
    dag_id: str,
    extract_specialist: ExtractSpecialist,
    extract_supervisor: ExtractSupervisor,
    transform_specialist: TransformSpecialist,
    transform_supervisor: TransformSupervisor,
    harness: Harness,
    load_gate: LoadGate,
    **dag_kwargs: Any,
):
    """Encadeia Extract -> Transform -> Harness -> Load numa DAG do Airflow.

    Extract reprovado interrompe a pipeline (raise -- vira falha de task,
    visível/alertável no Airflow): nada de inválido pode virar Bronze.
    Transform reprovado NÃO interrompe -- fica registrado em
    `metadata["transform_approved"]` para o Harness ponderar (é a Task 3,
    não a Task 2, que decide o destino final).
    """
    dag_kwargs.setdefault("schedule", None)
    dag_kwargs.setdefault("catchup", False)
    dag_kwargs.setdefault("default_args", {"retries": 2})
    dag_kwargs.setdefault("tags", ["data-agent-team"])

    @dag(dag_id=dag_id, **dag_kwargs)
    def _pipeline():
        @task()
        def extract() -> dict:
            record = extract_specialist.extract()
            verdict = extract_supervisor.review(record)
            if not verdict.approved:
                raise ValueError(
                    f"ExtractSupervisor reprovou '{record.source}': {verdict.details}"
                )
            return serialize_bronze(record)

        @task()
        def transform(bronze_data: dict) -> dict:
            bronze = deserialize_bronze(bronze_data)
            silver = transform_specialist.transform(bronze)
            verdict = transform_supervisor.review(bronze, silver)
            silver.metadata["transform_approved"] = verdict.approved
            if not verdict.approved:
                silver.metadata["transform_rejection_reasons"] = verdict.details
            return serialize_silver(silver)

        @task()
        def evaluate(silver_data: dict) -> dict:
            silver = deserialize_silver(silver_data)
            eval_result = harness.evaluate([silver])
            return serialize_eval_result(eval_result)

        @task()
        def load(silver_data: dict, eval_result_data: dict) -> str:
            silver = deserialize_silver(silver_data)
            eval_result = deserialize_eval_result(eval_result_data)
            return load_gate.load([silver], eval_result)

        bronze_data = extract()
        silver_data = transform(bronze_data)
        eval_result_data = evaluate(silver_data)
        load(silver_data, eval_result_data)

    return _pipeline()
