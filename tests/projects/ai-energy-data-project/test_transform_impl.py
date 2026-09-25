"""Testes de projects/ai-energy-data-project/transform_impl.py.

Carregado via importlib (mesma razão de test_extract_impl.py: a pasta do
projeto é kebab-case).
"""

import importlib.util
import pathlib
from unittest.mock import MagicMock, patch

from core.contracts import BronzeRecord, SilverRecord, SupervisorVerdict

_MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "projects"
    / "ai-energy-data-project"
    / "transform_impl.py"
)
_spec = importlib.util.spec_from_file_location("ai_energy_transform_impl", _MODULE_PATH)
transform_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transform_impl)

PdistChunkingTransformSpecialist = transform_impl.PdistChunkingTransformSpecialist
PdistFidelityTransformSupervisor = transform_impl.PdistFidelityTransformSupervisor
AneelTabularTransformSpecialist = transform_impl.AneelTabularTransformSpecialist
AneelTabularTransformSupervisor = transform_impl.AneelTabularTransformSupervisor

_SAMPLE_TEXT = (
    "8.1 Introdução\n"
    "Este módulo estabelece os procedimentos.\n"
    "8.1.1 Objetivo\n"
    "Definir os critérios de qualidade.\n"
)


def test_split_by_section_separates_by_numbered_heading():
    sections = PdistChunkingTransformSpecialist._split_by_section(_SAMPLE_TEXT)
    assert [numero for numero, _ in sections] == ["8.1", "8.1.1"]
    assert "Este módulo estabelece" in sections[0][1]
    assert "Definir os critérios" in sections[1][1]


def test_extract_text_joins_pages_with_pypdf():
    fake_reader = MagicMock()
    fake_reader.pages = [
        MagicMock(extract_text=lambda: "página um"),
        MagicMock(extract_text=lambda: "página dois"),
    ]
    with patch.object(transform_impl, "PdfReader", return_value=fake_reader):
        text = PdistChunkingTransformSpecialist._extract_text(b"%PDF-fake")
    assert text == "página um\npágina dois"


def test_transform_produces_silver_with_cleaned_chunks():
    generate = MagicMock(side_effect=lambda prompt: f"LIMPO::{prompt[-5:]}")
    specialist = PdistChunkingTransformSpecialist(
        source_name="prodist_pdf", generate=generate
    )
    bronze = BronzeRecord(source="prodist_pdf", raw_content=b"%PDF-fake")

    with patch.object(specialist, "_extract_text", return_value=_SAMPLE_TEXT):
        silver = specialist.transform(bronze)

    assert silver.bronze_ref == bronze.id
    assert silver.metadata == {
        "chunking_strategy": "por_secao_numerada",
        "chunk_count": 2,
    }
    assert len(silver.transformed_content) == 2
    assert silver.transformed_content[0]["secao"] == "8.1"
    assert silver.transformed_content[0]["texto_limpo"].startswith("LIMPO::")
    assert generate.call_count == 2


def test_transform_with_no_sections_returns_empty_chunks():
    specialist = PdistChunkingTransformSpecialist(
        source_name="prodist_pdf", generate=MagicMock()
    )
    bronze = BronzeRecord(source="prodist_pdf", raw_content=b"%PDF-fake")

    with patch.object(specialist, "_extract_text", return_value="texto sem numeração"):
        silver = specialist.transform(bronze)

    assert silver.transformed_content == []
    assert silver.metadata["chunk_count"] == 0


def _silver_with_chunks(*sections):
    return SilverRecord(
        transformed_content=[
            {"secao": secao, "texto_bruto": bruto, "texto_limpo": limpo}
            for secao, bruto, limpo in sections
        ]
    )


def test_review_approves_when_all_chunks_are_faithful():
    generate = MagicMock(return_value="SIM")
    supervisor = PdistFidelityTransformSupervisor(generate=generate)
    bronze = BronzeRecord()
    silver = _silver_with_chunks(("8.1", "bruto", "limpo"), ("8.2", "bruto2", "limpo2"))

    verdict = supervisor.review(bronze, silver)

    assert verdict.approved
    assert verdict.details == []
    assert generate.call_count == 2


def test_review_rejects_and_lists_unfaithful_sections():
    generate = MagicMock(side_effect=["SIM", "NAO"])
    supervisor = PdistFidelityTransformSupervisor(generate=generate)
    bronze = BronzeRecord()
    silver = _silver_with_chunks(
        ("8.1", "bruto", "limpo"), ("8.2", "bruto2", "alucinado")
    )

    verdict = supervisor.review(bronze, silver)

    assert not verdict.approved
    assert verdict.details == ["8.2"]


def test_review_approves_empty_chunk_list():
    supervisor = PdistFidelityTransformSupervisor(generate=MagicMock())
    verdict = supervisor.review(BronzeRecord(), SilverRecord(transformed_content=[]))
    assert verdict.approved
    assert verdict.details == []


# --- AneelTabularTransformSpecialist / AneelTabularTransformSupervisor ---

_ANEEL_ROWS = [
    {"conjunto": "ABC", "drp": 1.5},
    {"conjunto": "DEF", "drp": 0.8},
]


def test_aneel_tabular_transform_packages_rows_as_is():
    specialist = AneelTabularTransformSpecialist(source_name="aneel_drp_drc_parquet")
    bronze = BronzeRecord(
        source="aneel_drp_drc_parquet",
        raw_content=_ANEEL_ROWS,
        metadata={"completeness_ratio": 1.0},
    )

    silver = specialist.transform(bronze)

    assert silver.bronze_ref == bronze.id
    assert silver.transformed_content == _ANEEL_ROWS
    assert silver.metadata == {
        "row_count": 2,
        "completeness_ratio": 1.0,
        "expected_metadata_fields": ["row_count", "completeness_ratio"],
    }


def test_aneel_tabular_transform_handles_empty_rows():
    specialist = AneelTabularTransformSpecialist(source_name="aneel_dec_fec_parquet")
    bronze = BronzeRecord(raw_content=[], metadata={"completeness_ratio": 0.0})

    silver = specialist.transform(bronze)

    assert silver.transformed_content == []
    assert silver.metadata["row_count"] == 0


def test_aneel_tabular_review_approves_when_rows_preserved_and_consistent():
    bronze = BronzeRecord(raw_content=_ANEEL_ROWS)
    silver = SilverRecord(transformed_content=_ANEEL_ROWS)

    verdict = AneelTabularTransformSupervisor().review(bronze, silver)

    assert verdict == SupervisorVerdict(approved=True, details=[])


def test_aneel_tabular_review_fails_when_row_count_differs():
    bronze = BronzeRecord(raw_content=_ANEEL_ROWS)
    silver = SilverRecord(transformed_content=_ANEEL_ROWS[:1])

    verdict = AneelTabularTransformSupervisor().review(bronze, silver)

    assert not verdict.approved
    assert "linhas_preservadas" in verdict.details


def test_aneel_tabular_review_fails_when_schema_inconsistent():
    bronze = BronzeRecord(raw_content=_ANEEL_ROWS)
    inconsistent = [_ANEEL_ROWS[0], {"conjunto": "DEF"}]  # falta a coluna "drp"
    silver = SilverRecord(transformed_content=inconsistent)

    verdict = AneelTabularTransformSupervisor().review(bronze, silver)

    assert not verdict.approved
    assert "schema_consistente" in verdict.details


def test_aneel_tabular_review_skips_expected_columns_check_when_not_configured():
    bronze = BronzeRecord(raw_content=_ANEEL_ROWS)
    silver = SilverRecord(transformed_content=_ANEEL_ROWS)

    verdict = AneelTabularTransformSupervisor(expected_columns=None).review(
        bronze, silver
    )

    assert verdict.approved


def test_aneel_tabular_review_checks_expected_columns_when_configured():
    bronze = BronzeRecord(raw_content=_ANEEL_ROWS)
    silver = SilverRecord(transformed_content=_ANEEL_ROWS)
    supervisor = AneelTabularTransformSupervisor(
        expected_columns=["conjunto", "drp", "fec"]
    )

    verdict = supervisor.review(bronze, silver)

    assert not verdict.approved
    assert "colunas_esperadas" in verdict.details


def test_aneel_tabular_review_fails_closed_on_expected_columns_with_no_rows():
    bronze = BronzeRecord(raw_content=[])
    silver = SilverRecord(transformed_content=[])
    supervisor = AneelTabularTransformSupervisor(expected_columns=["conjunto"])

    verdict = supervisor.review(bronze, silver)

    assert not verdict.approved
    assert "colunas_esperadas" in verdict.details
