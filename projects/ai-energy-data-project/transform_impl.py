"""TransformSpecialist/TransformSupervisor concretos do projeto
ai-energy-data-project.

## prodist_pdf (chunking_strategy: por_secao_numerada, ver docs/ARCHITECTURE.md)

1. Extrai o texto do PDF (pypdf) -- determinístico.
2. Separa o texto em seções pelo padrão de numeração do PRODIST (ex.: "8.1",
   "8.1.1.1"), via regex -- determinístico, sem LLM.
3. Cada seção é "limpa" por um LLM (remove cabeçalho/rodapé de página e
   quebras de hifenização, sem alterar conteúdo normativo) -- aqui sim há
   julgamento semântico (o que é ruído de PDF vs. conteúdo real), por isso é
   Task 2 e não Task 1.
4. O TransformSupervisor pergunta ao LLM, por seção, se a limpeza foi fiel ao
   texto bruto -- reprova o lote se qualquer seção não for.

## aneel_drp_drc_parquet / aneel_dec_fec_parquet

Transform 100% determinístico -- decisão documentada em
`projects/ai-energy-data-project/docs/architecture.md`: o dado já vem
tipado/estruturado do Parquet (ver extract_impl.py), sem ambiguidade
textual, então não há julgamento semântico real a fazer. Forçar LLM aqui
violaria a própria regra não-negociável do framework ("LLM só onde há
julgamento semântico real").

Este módulo vive numa pasta kebab-case e é carregado via importlib -- ver o
docstring de extract_impl.py no mesmo diretório.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable

from pypdf import PdfReader

from core.contracts import BronzeRecord, SilverRecord, SupervisorVerdict
from core.transform.base import TransformSpecialist, TransformSupervisor

_SECTION_PATTERN = re.compile(
    r"^(?P<numero>\d+(?:\.\d+)+)\s+(?P<resto>.+)$", re.MULTILINE
)

_CLEAN_PROMPT = (
    "Remova cabeçalhos de página, rodapés e quebras de hifenização do texto "
    "normativo abaixo, sem alterar, resumir, parafrasear ou adicionar nenhuma "
    "palavra de conteúdo. Responda apenas com o texto limpo, nada mais.\n\n{texto}"
)

_FIDELITY_PROMPT = (
    "Responda apenas SIM ou NAO (sem pontuação). O texto B é uma limpeza do "
    "texto A -- remoção de cabeçalho/rodapé de página e de quebras de "
    "hifenização -- sem nenhuma alteração de conteúdo normativo, adição ou "
    "omissão?\n\nTexto A:\n{bruto}\n\nTexto B:\n{limpo}"
)


class PdistChunkingTransformSpecialist(TransformSpecialist):
    """Extrai o PDF, separa por seção numerada e limpa cada seção via LLM."""

    def __init__(self, source_name: str, generate: Callable[..., str]):
        self.source_name = source_name
        self.generate = generate

    def transform(self, record: BronzeRecord) -> SilverRecord:
        text = self._extract_text(record.raw_content)
        chunks = [
            {
                "secao": numero,
                "texto_bruto": texto_bruto,
                "texto_limpo": self._clean_section(texto_bruto),
            }
            for numero, texto_bruto in self._split_by_section(text)
        ]
        return SilverRecord(
            bronze_ref=record.id,
            transformed_content=chunks,
            metadata={
                "chunking_strategy": "por_secao_numerada",
                "chunk_count": len(chunks),
            },
        )

    @staticmethod
    def _extract_text(pdf_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _split_by_section(text: str) -> list[tuple[str, str]]:
        matches = list(_SECTION_PATTERN.finditer(text))
        sections = []
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((match.group("numero"), text[match.start() : end].strip()))
        return sections

    def _clean_section(self, texto_bruto: str) -> str:
        return self.generate(_CLEAN_PROMPT.format(texto=texto_bruto)).strip()


class PdistFidelityTransformSupervisor(TransformSupervisor):
    """Para cada chunk, pergunta ao LLM se a limpeza foi fiel ao texto bruto.
    Reprova o lote inteiro se qualquer seção não for julgada fiel.
    """

    def __init__(self, generate: Callable[..., str]):
        self.generate = generate

    def review(self, bronze: BronzeRecord, silver: SilverRecord) -> SupervisorVerdict:
        chunks = silver.transformed_content or []
        unfaithful = [
            chunk["secao"]
            for chunk in chunks
            if not self._is_faithful(chunk["texto_bruto"], chunk["texto_limpo"])
        ]
        return SupervisorVerdict(approved=not unfaithful, details=unfaithful)

    def _is_faithful(self, texto_bruto: str, texto_limpo: str) -> bool:
        prompt = _FIDELITY_PROMPT.format(bruto=texto_bruto, limpo=texto_limpo)
        return self.generate(prompt).strip().upper().startswith("SIM")


class AneelTabularTransformSpecialist(TransformSpecialist):
    """Transform determinístico para as fontes tabulares da ANEEL (DRP/DRC,
    DEC/FEC). `raw_content` já vem como `list[dict]` tipado do Parquet (ver
    extract_impl.py) -- não há limpeza/interpretação a fazer, só empacotar
    em SilverRecord preservando os dados.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    def transform(self, record: BronzeRecord) -> SilverRecord:
        rows = record.raw_content or []
        return SilverRecord(
            bronze_ref=record.id,
            transformed_content=rows,
            metadata={
                "row_count": len(rows),
                "completeness_ratio": record.metadata.get("completeness_ratio", 0.0),
            },
        )


class AneelTabularTransformSupervisor(TransformSupervisor):
    """Supervisor determinístico -- ver AneelTabularTransformSpecialist.

    `expected_columns` é opcional: o schema real dos resources Parquet ainda
    não foi inspecionado contra dado ao vivo (sem rede no ambiente de
    desenvolvimento), então por padrão a checagem de colunas não reprova por
    omissão -- só entra em vigor quando `expected_columns` for configurado
    (via config.yaml do projeto).
    """

    def __init__(self, expected_columns: list[str] | None = None):
        self.expected_columns = expected_columns

    def review(self, bronze: BronzeRecord, silver: SilverRecord) -> SupervisorVerdict:
        bronze_rows = bronze.raw_content or []
        silver_rows = silver.transformed_content or []

        checks = {
            "linhas_preservadas": len(silver_rows) == len(bronze_rows),
            "schema_consistente": self._has_consistent_schema(silver_rows),
        }
        if self.expected_columns:
            checks["colunas_esperadas"] = self._has_expected_columns(silver_rows)

        return SupervisorVerdict(
            approved=all(checks.values()),
            details=[name for name, passed in checks.items() if not passed],
        )

    @staticmethod
    def _has_consistent_schema(rows: list[dict]) -> bool:
        if not rows:
            return True
        first_keys = set(rows[0].keys())
        return all(set(row.keys()) == first_keys for row in rows)

    def _has_expected_columns(self, rows: list[dict]) -> bool:
        if not rows:
            return False
        expected = set(self.expected_columns)
        return all(expected.issubset(row.keys()) for row in rows)
