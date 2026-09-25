"""Métricas do Harness (Task 3), registradas via @register_metric.

Convenção: cada métrica é uma função pura `(sample: list[SilverRecord]) -> float`
(0.0 a 1.0), testável isoladamente, que lê **só `SilverRecord.metadata`** --
nunca a forma de `transformed_content`, que é específica de cada
TransformSpecialist. Isso mantém as métricas genéricas entre projetos: quem
monta o SilverRecord é responsável por popular a metadata que a métrica
escolhida no config.yaml do projeto precisa. Amostra vazia -> 0.0 (fail-closed,
mesmo princípio do ExtractSupervisor).

Chaves de metadata usadas abaixo:
- "transform_approved": bool -- setado pelo orquestrador com o resultado de
  TransformSupervisor.review() antes de entregar o SilverRecord ao Harness.
  É aqui que entra o "1 métrica de LLM-as-judge" citado em docs/ARCHITECTURE.md:
  o julgamento de LLM já aconteceu na Task 2: o Harness só agrega o resultado,
  não faz uma segunda chamada de LLM.
- "chunk_sizes": list[int] -- tamanho (em caracteres) de cada chunk final,
  populado pelo TransformSpecialist do projeto.
- "chunk_size_min" / "chunk_size_max": int, opcionais por registro -- limiares
  específicos do projeto (vêm do config.yaml via o TransformSpecialist); na
  ausência, usa os defaults deste módulo.
- "expected_metadata_fields": list[str], opcional -- quais chaves de metadata
  o projeto espera que o registro tenha preenchidas; na ausência, usa
  DEFAULT_EXPECTED_METADATA_FIELDS.
"""

from core.contracts import SilverRecord
from core.registry import register_metric

DEFAULT_CHUNK_SIZE_MIN = 50
DEFAULT_CHUNK_SIZE_MAX = 4000
DEFAULT_EXPECTED_METADATA_FIELDS = ("chunking_strategy", "chunk_count")


@register_metric("faithfulness_to_source")
def faithfulness_to_source(sample: list[SilverRecord]) -> float:
    """Fração dos registros do sample com `metadata['transform_approved'] is True`."""
    if not sample:
        return 0.0
    approved = sum(
        1 for record in sample if record.metadata.get("transform_approved") is True
    )
    return approved / len(sample)


@register_metric("chunk_size_valid")
def chunk_size_valid(sample: list[SilverRecord]) -> float:
    """Fração de chunks (agregando todos os registros do sample) com tamanho
    dentro de [chunk_size_min, chunk_size_max] -- evita chunks vazios (ruído)
    ou grandes demais (estouram limite de contexto/embedding).
    """
    results = []
    for record in sample:
        min_size = record.metadata.get("chunk_size_min", DEFAULT_CHUNK_SIZE_MIN)
        max_size = record.metadata.get("chunk_size_max", DEFAULT_CHUNK_SIZE_MAX)
        results.extend(
            min_size <= size <= max_size
            for size in record.metadata.get("chunk_sizes", [])
        )
    if not results:
        return 0.0
    return sum(results) / len(results)


@register_metric("metadata_extracted")
def metadata_extracted(sample: list[SilverRecord]) -> float:
    """Fração dos registros do sample cuja metadata contém todos os campos
    esperados (`metadata['expected_metadata_fields']`, com default genérico).
    """
    if not sample:
        return 0.0
    complete = sum(
        1
        for record in sample
        if all(
            field in record.metadata
            for field in record.metadata.get(
                "expected_metadata_fields", DEFAULT_EXPECTED_METADATA_FIELDS
            )
        )
    )
    return complete / len(sample)
