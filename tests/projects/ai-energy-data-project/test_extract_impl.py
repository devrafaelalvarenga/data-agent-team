"""Testes de projects/ai-energy-data-project/extract_impl.py.

O módulo é carregado via importlib (não `import`/`from`) porque a pasta do
projeto é kebab-case e não é um nome de pacote Python válido -- ver o
docstring de extract_impl.py.
"""

import datetime as dt
import importlib.util
import io
import json
import pathlib
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "projects"
    / "ai-energy-data-project"
    / "extract_impl.py"
)
_spec = importlib.util.spec_from_file_location("ai_energy_extract_impl", _MODULE_PATH)
extract_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract_impl)

AneelParquetExtractSpecialist = extract_impl.AneelParquetExtractSpecialist
ProdistPdfExtractSpecialist = extract_impl.ProdistPdfExtractSpecialist


def _mock_response(**overrides):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    for key, value in overrides.items():
        setattr(response, key, value)
    return response


def _parquet_bytes(rows: list[dict], schema: pa.Schema | None = None) -> bytes:
    table = pa.Table.from_pylist(rows, schema=schema)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


@pytest.fixture
def parquet_specialist():
    return AneelParquetExtractSpecialist(
        source_name="aneel_drp_drc_parquet",
        dataset_slug="indicadores-de-conformidade-do-nivel-de-tensao-em-regime-permanente",
        resource_name="indicadores-conformidade-nivel-tensao.parquet",
    )


def test_aneel_parquet_extract_downloads_resolved_resource(parquet_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao.parquet",
                        "format": "PARQUET",
                        "url": "https://dadosabertos.aneel.gov.br/fake.parquet",
                        "last_modified": "2026-09-01T12:00:00",
                    }
                ]
            }
        }
    )
    rows = [{"conjunto": "ABC", "drp": 1.5}, {"conjunto": "DEF", "drp": 0.8}]
    parquet_download_response = _mock_response(content=_parquet_bytes(rows))

    with patch.object(
        extract_impl.requests,
        "get",
        side_effect=[package_show_response, parquet_download_response],
    ) as mocked_get:
        record = parquet_specialist.extract()

    assert (
        mocked_get.call_args_list[1].args[0]
        == "https://dadosabertos.aneel.gov.br/fake.parquet"
    )
    assert record.source == "aneel_drp_drc_parquet"
    assert record.raw_content == rows
    assert record.metadata["row_count"] == 2
    assert record.metadata["completeness_ratio"] == 1.0
    assert record.metadata["source_updated_at"] == "2026-09-01T12:00:00+00:00"


def test_aneel_parquet_extract_converts_date_and_decimal_to_json_safe(
    parquet_specialist,
):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao.parquet",
                        "format": "PARQUET",
                        "url": "https://dadosabertos.aneel.gov.br/fake.parquet",
                    }
                ]
            }
        }
    )
    schema = pa.schema(
        [("data_referencia", pa.date32()), ("valor", pa.decimal128(10, 2))]
    )
    rows = [{"data_referencia": dt.date(2026, 1, 1), "valor": Decimal("12.34")}]
    parquet_download_response = _mock_response(
        content=_parquet_bytes(rows, schema=schema)
    )

    with patch.object(
        extract_impl.requests,
        "get",
        side_effect=[package_show_response, parquet_download_response],
    ):
        record = parquet_specialist.extract()

    row = record.raw_content[0]
    assert row["data_referencia"] == "2026-01-01"
    assert row["valor"] == 12.34
    json.dumps(record.raw_content)  # não deve levantar TypeError


def test_aneel_parquet_extract_empty_result_has_zero_completeness(parquet_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao.parquet",
                        "format": "PARQUET",
                        "url": "https://dadosabertos.aneel.gov.br/fake.parquet",
                    }
                ]
            }
        }
    )
    parquet_download_response = _mock_response(
        content=_parquet_bytes([], schema=pa.schema([("conjunto", pa.string())]))
    )

    with patch.object(
        extract_impl.requests,
        "get",
        side_effect=[package_show_response, parquet_download_response],
    ):
        record = parquet_specialist.extract()

    assert record.raw_content == []
    assert record.metadata["completeness_ratio"] == 0.0


def test_aneel_parquet_extract_raises_when_resource_missing(parquet_specialist):
    package_show_response = _mock_response(json=lambda: {"result": {"resources": []}})

    with (
        patch.object(extract_impl.requests, "get", return_value=package_show_response),
        pytest.raises(ValueError, match="não encontrado"),
    ):
        parquet_specialist.extract()


def test_aneel_parquet_extract_raises_when_resource_not_parquet(parquet_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao.parquet",
                        "format": "ZIP",
                        "url": "https://dadosabertos.aneel.gov.br/fake.zip",
                    }
                ]
            }
        }
    )

    with (
        patch.object(extract_impl.requests, "get", return_value=package_show_response),
        pytest.raises(ValueError, match="não é Parquet"),
    ):
        parquet_specialist.extract()


def test_prodist_pdf_extract_downloads_and_parses_last_modified():
    specialist = ProdistPdfExtractSpecialist(
        source_name="prodist_pdf",
        url="https://git.aneel.gov.br/publico/centralconteudo/-/raw/main/procreg/prodist/modulo08/aren20251137_Prodist_modulo_8_v14.pdf",
    )
    response = _mock_response(
        content=b"%PDF-1.4 fake bytes",
        headers={
            "Content-Type": "application/pdf",
            "Last-Modified": "Tue, 01 Sep 2026 12:00:00 GMT",
        },
    )

    with patch.object(
        extract_impl.requests, "get", return_value=response
    ) as mocked_get:
        record = specialist.extract()

    mocked_get.assert_called_once_with(specialist.url, timeout=specialist.timeout)
    assert record.source == "prodist_pdf"
    assert record.raw_content == b"%PDF-1.4 fake bytes"
    assert record.metadata["content_type"] == "application/pdf"
    assert record.metadata["byte_size"] == len(b"%PDF-1.4 fake bytes")
    assert record.metadata["completeness_ratio"] == 1.0
    assert record.metadata["source_updated_at"] == "2026-09-01T12:00:00+00:00"


def test_prodist_pdf_extract_falls_back_to_now_without_last_modified():
    specialist = ProdistPdfExtractSpecialist(
        source_name="prodist_pdf", url="https://example.org/x.pdf"
    )
    response = _mock_response(content=b"data", headers={})

    with patch.object(extract_impl.requests, "get", return_value=response):
        record = specialist.extract()

    assert record.metadata["source_updated_at"]
