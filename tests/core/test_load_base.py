from datetime import datetime
from unittest.mock import MagicMock

from core.contracts import EvalResult, SilverRecord
from core.load.base import LoadGate


def test_load_writes_to_gold_when_passed():
    gold_writer = MagicMock()
    audit_writer = MagicMock()
    gate = LoadGate(gold_writer=gold_writer, audit_writer=audit_writer)
    records = [SilverRecord(), SilverRecord()]
    eval_result = EvalResult(
        score=0.9, passed=True, breakdown={"faithfulness_to_source": 0.9}
    )

    destination = gate.load(records, eval_result)

    assert destination == "gold"
    gold_writer.assert_called_once_with(records)
    audit_writer.assert_not_called()


def test_load_writes_to_audit_when_not_passed():
    gold_writer = MagicMock()
    audit_writer = MagicMock()
    gate = LoadGate(gold_writer=gold_writer, audit_writer=audit_writer)
    record = SilverRecord(
        transformed_content=[{"secao": "8.1"}], metadata={"chunk_count": 1}
    )
    eval_result = EvalResult(
        score=0.3, passed=False, breakdown={"faithfulness_to_source": 0.3}
    )

    destination = gate.load([record], eval_result)

    assert destination == "audit"
    gold_writer.assert_not_called()
    audit_writer.assert_called_once()

    (audit_records,), _ = audit_writer.call_args
    assert len(audit_records) == 1
    audit_record = audit_records[0]
    assert audit_record.silver_ref == record.id
    assert audit_record.reason == {"faithfulness_to_source": 0.3}
    assert audit_record.raw_content == [{"secao": "8.1"}]
    assert audit_record.metadata == {"chunk_count": 1}
    datetime.fromisoformat(audit_record.rejected_at)


def test_load_creates_one_audit_record_per_silver_record():
    gate = LoadGate(gold_writer=MagicMock(), audit_writer=(audit_writer := MagicMock()))
    records = [SilverRecord(), SilverRecord(), SilverRecord()]
    eval_result = EvalResult(score=0.1, passed=False, breakdown={})

    gate.load(records, eval_result)

    (audit_records,), _ = audit_writer.call_args
    assert [r.silver_ref for r in audit_records] == [r.id for r in records]
