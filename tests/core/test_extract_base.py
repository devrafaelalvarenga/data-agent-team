from datetime import UTC, datetime, timedelta

import pytest

from core.contracts import BronzeRecord, SupervisorVerdict
from core.extract.base import ExtractSpecialist, ExtractSupervisor


class _FakeExtractSpecialist(ExtractSpecialist):
    def extract(self) -> BronzeRecord:
        return BronzeRecord(source="fake")


def test_extract_specialist_is_abstract():
    with pytest.raises(TypeError):
        ExtractSpecialist()


def test_extract_specialist_subclass_implements_extract():
    record = _FakeExtractSpecialist().extract()
    assert record.source == "fake"


def _valid_record(**overrides) -> BronzeRecord:
    metadata = {
        "row_count": 10,
        "completeness_ratio": 1.0,
        "source_updated_at": datetime.now(UTC).isoformat(),
    }
    metadata.update(overrides)
    return BronzeRecord(metadata=metadata)


def _supervisor(**overrides) -> ExtractSupervisor:
    kwargs = {
        "schema_rules": {"row_count": int},
        "completeness_min_ratio": 0.95,
        "freshness_max_hours": 24,
    }
    kwargs.update(overrides)
    return ExtractSupervisor(**kwargs)


def test_review_approves_when_all_checks_pass():
    verdict = _supervisor().review(_valid_record())
    assert verdict == SupervisorVerdict(approved=True, details=[])


def test_review_fails_schema_when_field_missing():
    record = _valid_record()
    del record.metadata["row_count"]
    verdict = _supervisor().review(record)
    assert not verdict.approved
    assert "schema_valido" in verdict.details


def test_review_fails_schema_when_type_mismatch():
    record = _valid_record(row_count="10")
    verdict = _supervisor().review(record)
    assert "schema_valido" in verdict.details


def test_review_fails_completeness_below_threshold():
    record = _valid_record(completeness_ratio=0.5)
    verdict = _supervisor().review(record)
    assert "completo" in verdict.details


def test_review_fails_completeness_when_missing():
    record = _valid_record()
    del record.metadata["completeness_ratio"]
    verdict = _supervisor().review(record)
    assert "completo" in verdict.details


def test_review_fails_freshness_when_too_old():
    stale = datetime.now(UTC) - timedelta(hours=48)
    record = _valid_record(source_updated_at=stale.isoformat())
    verdict = _supervisor().review(record)
    assert "atualizado" in verdict.details


def test_review_fails_freshness_when_missing():
    record = _valid_record()
    del record.metadata["source_updated_at"]
    verdict = _supervisor().review(record)
    assert "atualizado" in verdict.details


def test_review_lists_all_failed_checks():
    record = BronzeRecord(metadata={})
    verdict = _supervisor().review(record)
    assert not verdict.approved
    assert set(verdict.details) == {"schema_valido", "completo", "atualizado"}
