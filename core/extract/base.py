"""Extract: lê dados brutos da fonte (specialist) e valida antes de liberar para Bronze
(supervisor). Ver docs/ARCHITECTURE.md, seção "As 4 Tasks".
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from core.contracts import BronzeRecord, SupervisorVerdict


class ExtractSpecialist(ABC):
    """Cada projeto implementa isso com sua lógica de extração específica."""

    @abstractmethod
    def extract(self) -> BronzeRecord: ...


class ExtractSupervisor:
    """Genérico -- a lógica das checagens é a mesma em qualquer projeto, mas os
    limiares vêm de config.yaml (cada fonte pode ter regras diferentes: 'atualizado'
    significa algo distinto para um PDF normativo e para um CSV mensal).

    Convenção que o ExtractSpecialist deve popular em BronzeRecord.metadata para que
    os checks abaixo funcionem:
    - as chaves declaradas em `schema_rules` (nome -> tipo esperado)
    - "completeness_ratio": float entre 0 e 1
    - "source_updated_at": timestamp ISO 8601 de quando a fonte foi atualizada

    Qualquer chave ausente ou malformada reprova o check correspondente (fail-closed):
    um supervisor que não consegue verificar não deve aprovar por omissão.
    """

    def __init__(
        self,
        schema_rules: dict[str, type],
        completeness_min_ratio: float,
        freshness_max_hours: int,
    ):
        self.schema_rules = schema_rules
        self.completeness_min_ratio = completeness_min_ratio
        self.freshness_max_hours = freshness_max_hours

    def review(self, record: BronzeRecord) -> SupervisorVerdict:
        checks = {
            "schema_valido": self._check_schema(record),
            "completo": self._check_completeness(record),
            "atualizado": self._check_freshness(record),
        }
        return SupervisorVerdict(
            approved=all(checks.values()),
            details=[name for name, passed in checks.items() if not passed],
        )

    def _check_schema(self, record: BronzeRecord) -> bool:
        return all(
            isinstance(record.metadata.get(field), expected_type)
            for field, expected_type in self.schema_rules.items()
        )

    def _check_completeness(self, record: BronzeRecord) -> bool:
        ratio = record.metadata.get("completeness_ratio")
        if not isinstance(ratio, (int, float)):
            return False
        return ratio >= self.completeness_min_ratio

    def _check_freshness(self, record: BronzeRecord) -> bool:
        updated_at = record.metadata.get("source_updated_at")
        if not isinstance(updated_at, str):
            return False
        try:
            updated = datetime.fromisoformat(updated_at)
        except ValueError:
            return False
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - updated).total_seconds() / 3600
        return age_hours <= self.freshness_max_hours
