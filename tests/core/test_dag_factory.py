"""Testes de core/orchestration/dag_factory.py sem depender de `airflow` de
verdade: injeta um `airflow.sdk` fake em sys.modules (`@dag`/`@task` como
no-ops que só chamam a função decorada) para validar o encadeamento e a
serialização entre as 4 Tasks. Não substitui validação real -- essa exige
`astro dev pytest` ou `astro dev start` dentro do container do Astro.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

LAST_DAG_KWARGS: dict = {}


def _install_fake_airflow_sdk():
    fake_sdk = types.ModuleType("airflow.sdk")

    def fake_task(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator

    def fake_dag(*_args, **kwargs):
        LAST_DAG_KWARGS.clear()
        LAST_DAG_KWARGS.update(kwargs)

        def decorator(fn):
            def wrapper(*a, **kw):
                return fn(*a, **kw)

            return wrapper

        return decorator

    fake_sdk.task = fake_task
    fake_sdk.dag = fake_dag

    fake_airflow = types.ModuleType("airflow")
    fake_airflow.sdk = fake_sdk
    sys.modules["airflow"] = fake_airflow
    sys.modules["airflow.sdk"] = fake_sdk


_install_fake_airflow_sdk()

from core.contracts import (
    BronzeRecord,
    EvalResult,
    SilverRecord,
    SupervisorVerdict,
)
from core.orchestration.dag_factory import build_pipeline_dag


def _components(*, extract_approved=True, transform_approved=True, eval_passed=True):
    bronze = BronzeRecord(source="prodist_pdf", raw_content=b"%PDF-x", metadata={})
    silver = SilverRecord(
        bronze_ref=bronze.id, transformed_content=[{"secao": "8.1"}], metadata={}
    )

    extract_specialist = MagicMock(extract=MagicMock(return_value=bronze))
    extract_supervisor = MagicMock(
        review=MagicMock(
            return_value=SupervisorVerdict(
                approved=extract_approved, details=[] if extract_approved else ["ruim"]
            )
        )
    )
    transform_specialist = MagicMock(transform=MagicMock(return_value=silver))
    transform_supervisor = MagicMock(
        review=MagicMock(
            return_value=SupervisorVerdict(
                approved=transform_approved,
                details=[] if transform_approved else ["infiel"],
            )
        )
    )
    harness = MagicMock(
        evaluate=MagicMock(
            return_value=EvalResult(
                score=0.9 if eval_passed else 0.1,
                passed=eval_passed,
                breakdown={"m": 0.9},
            )
        )
    )
    load_gate = MagicMock(
        load=MagicMock(return_value="gold" if eval_passed else "audit")
    )

    return {
        "bronze": bronze,
        "silver": silver,
        "extract_specialist": extract_specialist,
        "extract_supervisor": extract_supervisor,
        "transform_specialist": transform_specialist,
        "transform_supervisor": transform_supervisor,
        "harness": harness,
        "load_gate": load_gate,
    }


def _run(c):
    build_pipeline_dag(
        dag_id="test_dag",
        extract_specialist=c["extract_specialist"],
        extract_supervisor=c["extract_supervisor"],
        transform_specialist=c["transform_specialist"],
        transform_supervisor=c["transform_supervisor"],
        harness=c["harness"],
        load_gate=c["load_gate"],
    )


def test_pipeline_runs_happy_path_and_threads_data_between_tasks():
    components = _components()
    _run(components)

    components["extract_specialist"].extract.assert_called_once()
    components["extract_supervisor"].review.assert_called_once_with(
        components["bronze"]
    )

    (transform_bronze,), _ = components["transform_specialist"].transform.call_args
    assert transform_bronze == components["bronze"]

    review_bronze, _review_silver = components[
        "transform_supervisor"
    ].review.call_args.args
    assert review_bronze == components["bronze"]

    (harness_sample,), _ = components["harness"].evaluate.call_args
    assert harness_sample[0].bronze_ref == components["silver"].bronze_ref
    assert harness_sample[0].metadata["transform_approved"] is True

    load_records, load_eval = components["load_gate"].load.call_args.args
    assert load_records[0].metadata["transform_approved"] is True
    assert load_eval == EvalResult(score=0.9, passed=True, breakdown={"m": 0.9})


def test_pipeline_raises_when_extract_supervisor_rejects():
    c = _components(extract_approved=False)
    with pytest.raises(ValueError, match="ruim"):
        _run(c)
    c["transform_specialist"].transform.assert_not_called()


def test_pipeline_continues_when_transform_supervisor_rejects():
    c = _components(transform_approved=False, eval_passed=False)
    _run(c)

    (harness_sample,), _ = c["harness"].evaluate.call_args
    assert harness_sample[0].metadata["transform_approved"] is False
    assert harness_sample[0].metadata["transform_rejection_reasons"] == ["infiel"]
    c["load_gate"].load.assert_called_once()


def test_pipeline_dag_has_sane_defaults():
    _run(_components())
    assert LAST_DAG_KWARGS["schedule"] is None
    assert LAST_DAG_KWARGS["catchup"] is False
    assert LAST_DAG_KWARGS["default_args"]["retries"] >= 2
    assert "data-agent-team" in LAST_DAG_KWARGS["tags"]
