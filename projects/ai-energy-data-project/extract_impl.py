"""ExtractSpecialists concretos do projeto ai-energy-data-project.

Fontes (ver docs/ARCHITECTURE.md):
- prodist_pdf: PRODIST Módulo 8, documento normativo estático publicado
  pela ANEEL -- baixado de uma URL fixa (config.yaml).
- aneel_drp_drc_parquet / aneel_dec_fec_parquet: publicados no Portal de
  Dados Abertos da ANEEL (https://dadosabertos.aneel.gov.br), que é um CKAN.
  Parquet em vez de CSV: schema tipado embutido (sem precisar declarar tipo
  de coluna via config.yaml) e carga nativa mais eficiente no BigQuery. O
  resource é resolvido dinamicamente via `package_show` da API do CKAN, em
  vez da URL de download ser hardcoded: o UUID do resource muda quando a
  ANEEL republica o dataset, mas o slug do dataset e o nome do resource são
  estáveis -- ambos vêm do config.yaml do projeto.

Este módulo vive numa pasta kebab-case (`projects/ai-energy-data-project/`),
que não é um nome de pacote Python válido para import por ponto. Ele é
carregado por caminho (importlib) por quem for orquestrar o pipeline
(futuramente `core/orchestration/dag_factory.py`), nunca via
`from projects.ai_energy_data_project import extract_impl`.
"""

from __future__ import annotations

import datetime as dt
import io
from decimal import Decimal
from email.utils import parsedate_to_datetime

import pyarrow.parquet as pq
import requests

from core.contracts import BronzeRecord
from core.extract.base import ExtractSpecialist

CKAN_API_BASE = "https://dadosabertos.aneel.gov.br/api/3/action"


def _json_safe_value(value):
    """pyarrow devolve `datetime.date`/`datetime.datetime`/`Decimal` para
    colunas de data e numéricas de precisão fixa -- nenhum dos dois é
    JSON-safe (necessário para trafegar em BronzeRecord.raw_content via XCom,
    ver core/orchestration/serialization.py)."""
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _json_safe_row(row: dict) -> dict:
    return {key: _json_safe_value(value) for key, value in row.items()}


class AneelParquetExtractSpecialist(ExtractSpecialist):
    """Baixa um resource Parquet de um dataset do Portal de Dados Abertos da
    ANEEL.

    Usado tanto para 'aneel_drp_drc_parquet' quanto para
    'aneel_dec_fec_parquet' -- estruturalmente é a mesma operação; o que
    muda (dataset, resource) vem do config.yaml do projeto.
    """

    def __init__(
        self,
        source_name: str,
        dataset_slug: str,
        resource_name: str,
        timeout: int = 30,
    ):
        self.source_name = source_name
        self.dataset_slug = dataset_slug
        self.resource_name = resource_name
        self.timeout = timeout

    def extract(self) -> BronzeRecord:
        resource = self._resolve_resource()
        response = requests.get(resource["url"], timeout=self.timeout)
        response.raise_for_status()
        table = pq.read_table(io.BytesIO(response.content))
        rows = [_json_safe_row(row) for row in table.to_pylist()]
        return BronzeRecord(
            source=self.source_name,
            raw_content=rows,
            metadata={
                "resource_name": self.resource_name,
                "row_count": len(rows),
                "completeness_ratio": 1.0 if rows else 0.0,
                "source_updated_at": self._resolve_updated_at(resource),
            },
        )

    def _resolve_resource(self) -> dict:
        response = requests.get(
            f"{CKAN_API_BASE}/package_show",
            params={"id": self.dataset_slug},
            timeout=self.timeout,
        )
        response.raise_for_status()
        resources = response.json()["result"]["resources"]
        for resource in resources:
            if resource["name"] == self.resource_name:
                if resource["format"].upper() != "PARQUET":
                    raise ValueError(
                        f"resource '{self.resource_name}' não é Parquet "
                        f"(formato: {resource['format']})"
                    )
                return resource
        raise ValueError(
            f"resource '{self.resource_name}' não encontrado no dataset "
            f"'{self.dataset_slug}'"
        )

    @staticmethod
    def _resolve_updated_at(resource: dict) -> str:
        updated_at = resource.get("last_modified") or resource.get("created")
        if not updated_at:
            return dt.datetime.now(dt.UTC).isoformat()
        if updated_at.endswith("Z") or "+" in updated_at:
            return updated_at
        return f"{updated_at}+00:00"


class ProdistPdfExtractSpecialist(ExtractSpecialist):
    """Baixa o PDF do PRODIST Módulo 8, documento normativo estático da ANEEL."""

    def __init__(self, source_name: str, url: str, timeout: int = 60):
        self.source_name = source_name
        self.url = url
        self.timeout = timeout

    def extract(self) -> BronzeRecord:
        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return BronzeRecord(
            source=self.source_name,
            raw_content=response.content,
            metadata={
                "content_type": response.headers.get("Content-Type", ""),
                "byte_size": len(response.content),
                "completeness_ratio": 1.0 if response.content else 0.0,
                "source_updated_at": self._parse_http_date(
                    response.headers.get("Last-Modified")
                ),
            },
        )

    @staticmethod
    def _parse_http_date(value: str | None) -> str:
        if not value:
            return dt.datetime.now(dt.UTC).isoformat()
        return parsedate_to_datetime(value).astimezone(dt.UTC).isoformat()
