from core.contracts import (
    AuditRecord,
    BronzeRecord,
    EvalResult,
    SilverRecord,
    SupervisorVerdict,
)


def test_bronze_record_defaults():
    record = BronzeRecord()
    assert record.id
    assert record.source == ""
    assert record.raw_content is None
    assert record.metadata == {}


def test_bronze_record_ids_are_unique():
    assert BronzeRecord().id != BronzeRecord().id


def test_bronze_record_metadata_is_not_shared_between_instances():
    a, b = BronzeRecord(), BronzeRecord()
    a.metadata["k"] = "v"
    assert b.metadata == {}


def test_silver_record_references_bronze():
    bronze = BronzeRecord()
    silver = SilverRecord(bronze_ref=bronze.id, transformed_content={"chunks": []})
    assert silver.bronze_ref == bronze.id
    assert silver.id != bronze.id


def test_supervisor_verdict_approved_with_no_details():
    verdict = SupervisorVerdict(approved=True, details=[])
    assert verdict.approved
    assert verdict.details == []


def test_supervisor_verdict_rejected_lists_failed_checks():
    verdict = SupervisorVerdict(approved=False, details=["completo", "atualizado"])
    assert not verdict.approved
    assert verdict.details == ["completo", "atualizado"]


def test_eval_result_holds_breakdown():
    result = EvalResult(
        score=0.9, passed=True, breakdown={"faithfulness_to_source": 0.9}
    )
    assert result.passed
    assert result.breakdown["faithfulness_to_source"] == 0.9


def test_audit_record_requires_explicit_fields():
    silver = SilverRecord()
    record = AuditRecord(
        silver_ref=silver.id,
        reason={"faithfulness_to_source": 0.4},
        rejected_at="2026-09-24T00:00:00+00:00",
        raw_content={"text": "..."},
    )
    assert record.silver_ref == silver.id
    assert record.metadata == {}
