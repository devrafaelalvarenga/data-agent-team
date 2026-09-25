from core.contracts import BronzeRecord, SilverRecord
from core.orchestration.serialization import (
    deserialize_bronze,
    deserialize_silver,
    serialize_bronze,
    serialize_silver,
)


def test_serialize_bronze_with_text_content_roundtrips():
    record = BronzeRecord(
        source="aneel_drp_drc_csv", raw_content=[{"a": "1"}], metadata={"row_count": 1}
    )
    data = serialize_bronze(record)
    assert data["raw_content"] == [{"a": "1"}]
    assert "raw_content_is_b64" not in data

    restored = deserialize_bronze(data)
    assert restored == record


def test_serialize_bronze_with_bytes_content_base64_roundtrips():
    record = BronzeRecord(
        source="prodist_pdf", raw_content=b"%PDF-fake-bytes", metadata={}
    )
    data = serialize_bronze(record)

    assert isinstance(data["raw_content"], str)
    assert data["raw_content_is_b64"] is True

    restored = deserialize_bronze(data)
    assert restored.raw_content == b"%PDF-fake-bytes"
    assert restored == record


def test_serialize_bronze_is_json_safe_for_bytes_payload():
    import json

    record = BronzeRecord(source="prodist_pdf", raw_content=b"\x00\x01\xff binary")
    data = serialize_bronze(record)
    json.dumps(data)  # não deve levantar TypeError


def test_serialize_silver_roundtrips():
    record = SilverRecord(
        bronze_ref="abc",
        transformed_content=[{"secao": "8.1", "texto_limpo": "x"}],
        metadata={"chunk_count": 1},
    )
    data = serialize_silver(record)
    assert data["bronze_ref"] == "abc"

    restored = deserialize_silver(data)
    assert restored == record
