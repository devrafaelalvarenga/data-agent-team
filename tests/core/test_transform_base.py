import pytest

from core.contracts import BronzeRecord, SilverRecord, SupervisorVerdict
from core.transform.base import TransformSpecialist, TransformSupervisor


class _FakeTransformSpecialist(TransformSpecialist):
    def transform(self, record: BronzeRecord) -> SilverRecord:
        return SilverRecord(
            bronze_ref=record.id, transformed_content=record.raw_content
        )


class _FakeTransformSupervisor(TransformSupervisor):
    def review(self, bronze: BronzeRecord, silver: SilverRecord) -> SupervisorVerdict:
        faithful = silver.transformed_content == bronze.raw_content
        return SupervisorVerdict(
            approved=faithful, details=[] if faithful else ["fidelidade"]
        )


def test_transform_specialist_is_abstract():
    with pytest.raises(TypeError):
        TransformSpecialist()


def test_transform_supervisor_is_abstract():
    with pytest.raises(TypeError):
        TransformSupervisor()


def test_transform_specialist_subclass_produces_silver_linked_to_bronze():
    bronze = BronzeRecord(raw_content="texto bruto")
    silver = _FakeTransformSpecialist().transform(bronze)
    assert silver.bronze_ref == bronze.id
    assert silver.transformed_content == "texto bruto"


def test_transform_supervisor_subclass_approves_faithful_transformation():
    bronze = BronzeRecord(raw_content="texto bruto")
    silver = SilverRecord(bronze_ref=bronze.id, transformed_content="texto bruto")
    verdict = _FakeTransformSupervisor().review(bronze, silver)
    assert verdict == SupervisorVerdict(approved=True, details=[])


def test_transform_supervisor_subclass_rejects_unfaithful_transformation():
    bronze = BronzeRecord(raw_content="texto bruto")
    silver = SilverRecord(bronze_ref=bronze.id, transformed_content="alucinação")
    verdict = _FakeTransformSupervisor().review(bronze, silver)
    assert not verdict.approved
    assert verdict.details == ["fidelidade"]
