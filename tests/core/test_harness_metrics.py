from core.contracts import SilverRecord
from core.harness.metrics import (
    chunk_size_valid,
    faithfulness_to_source,
    metadata_extracted,
)
from core.registry import METRIC_REGISTRY


def test_metrics_are_registered():
    assert METRIC_REGISTRY["faithfulness_to_source"] is faithfulness_to_source
    assert METRIC_REGISTRY["chunk_size_valid"] is chunk_size_valid
    assert METRIC_REGISTRY["metadata_extracted"] is metadata_extracted


def test_faithfulness_to_source_empty_sample_is_zero():
    assert faithfulness_to_source([]) == 0.0


def test_faithfulness_to_source_all_approved():
    sample = [SilverRecord(metadata={"transform_approved": True}) for _ in range(3)]
    assert faithfulness_to_source(sample) == 1.0


def test_faithfulness_to_source_partial_approval():
    sample = [
        SilverRecord(metadata={"transform_approved": True}),
        SilverRecord(metadata={"transform_approved": False}),
    ]
    assert faithfulness_to_source(sample) == 0.5


def test_faithfulness_to_source_missing_key_is_fail_closed():
    sample = [
        SilverRecord(metadata={}),
        SilverRecord(metadata={"transform_approved": True}),
    ]
    assert faithfulness_to_source(sample) == 0.5


def test_chunk_size_valid_empty_sample_is_zero():
    assert chunk_size_valid([]) == 0.0


def test_chunk_size_valid_no_chunk_sizes_is_zero():
    assert chunk_size_valid([SilverRecord(metadata={})]) == 0.0


def test_chunk_size_valid_uses_default_thresholds():
    sample = [SilverRecord(metadata={"chunk_sizes": [100, 10, 5000]})]
    assert chunk_size_valid(sample) == 1 / 3


def test_chunk_size_valid_uses_custom_thresholds_per_record():
    sample = [
        SilverRecord(
            metadata={
                "chunk_sizes": [10, 20],
                "chunk_size_min": 5,
                "chunk_size_max": 15,
            }
        )
    ]
    assert chunk_size_valid(sample) == 0.5


def test_metadata_extracted_empty_sample_is_zero():
    assert metadata_extracted([]) == 0.0


def test_metadata_extracted_default_expected_fields():
    complete = SilverRecord(metadata={"chunking_strategy": "x", "chunk_count": 2})
    incomplete = SilverRecord(metadata={"chunking_strategy": "x"})
    assert metadata_extracted([complete, incomplete]) == 0.5


def test_metadata_extracted_custom_expected_fields():
    sample = [
        SilverRecord(metadata={"expected_metadata_fields": ["secao"], "secao": "8.1"}),
        SilverRecord(metadata={"expected_metadata_fields": ["secao"]}),
    ]
    assert metadata_extracted(sample) == 0.5
