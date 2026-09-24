"""Testes de projects/ai-energy-data-project/extract_impl.py.

O módulo é carregado via importlib (não `import`/`from`) porque a pasta do
projeto é kebab-case e não é um nome de pacote Python válido -- ver o
docstring de extract_impl.py.
"""

import importlib.util
import pathlib
from unittest.mock import MagicMock, patch

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

AneelCsvExtractSpecialist = extract_impl.AneelCsvExtractSpecialist
ProdistPdfExtractSpecialist = extract_impl.ProdistPdfExtractSpecialist


def _mock_response(**overrides):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    for key, value in overrides.items():
        setattr(response, key, value)
    return response


@pytest.fixture
def csv_specialist():
    return AneelCsvExtractSpecialist(
        source_name="aneel_drp_drc_csv",
        dataset_slug="indicadores-de-conformidade-do-nivel-de-tensao-em-regime-permanente",
        resource_name="indicadores-conformidade-nivel-tensao",
    )


def test_aneel_csv_extract_downloads_resolved_resource(csv_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao",
                        "format": "CSV",
                        "url": "https://dadosabertos.aneel.gov.br/fake.csv",
                        "last_modified": "2026-09-01T12:00:00",
                    }
                ]
            }
        }
    )
    csv_download_response = _mock_response(text="conjunto,drp\nABC,1.5\nDEF,0.8\n")

    with patch.object(
        extract_impl.requests,
        "get",
        side_effect=[package_show_response, csv_download_response],
    ) as mocked_get:
        record = csv_specialist.extract()

    assert (
        mocked_get.call_args_list[1].args[0]
        == "https://dadosabertos.aneel.gov.br/fake.csv"
    )
    assert record.source == "aneel_drp_drc_csv"
    assert record.raw_content == [
        {"conjunto": "ABC", "drp": "1.5"},
        {"conjunto": "DEF", "drp": "0.8"},
    ]
    assert record.metadata["row_count"] == 2
    assert record.metadata["completeness_ratio"] == 1.0
    assert record.metadata["source_updated_at"] == "2026-09-01T12:00:00+00:00"


def test_aneel_csv_extract_empty_result_has_zero_completeness(csv_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao",
                        "format": "CSV",
                        "url": "https://dadosabertos.aneel.gov.br/fake.csv",
                    }
                ]
            }
        }
    )
    csv_download_response = _mock_response(text="")

    with patch.object(
        extract_impl.requests,
        "get",
        side_effect=[package_show_response, csv_download_response],
    ):
        record = csv_specialist.extract()

    assert record.raw_content == []
    assert record.metadata["completeness_ratio"] == 0.0


def test_aneel_csv_extract_raises_when_resource_missing(csv_specialist):
    package_show_response = _mock_response(json=lambda: {"result": {"resources": []}})

    with (
        patch.object(extract_impl.requests, "get", return_value=package_show_response),
        pytest.raises(ValueError, match="não encontrado"),
    ):
        csv_specialist.extract()


def test_aneel_csv_extract_raises_when_resource_not_csv(csv_specialist):
    package_show_response = _mock_response(
        json=lambda: {
            "result": {
                "resources": [
                    {
                        "name": "indicadores-conformidade-nivel-tensao",
                        "format": "ZIP",
                        "url": "https://dadosabertos.aneel.gov.br/fake.zip",
                    }
                ]
            }
        }
    )

    with (
        patch.object(extract_impl.requests, "get", return_value=package_show_response),
        pytest.raises(ValueError, match="não é CSV"),
    ):
        csv_specialist.extract()


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
