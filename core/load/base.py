"""Load (Task 4): decide o destino com base no EvalResult do Harness.
Sempre determinístico -- nunca implementar como agente LLM. Ver
docs/ARCHITECTURE.md, seção "As 4 Tasks".
"""

from collections.abc import Callable
from datetime import UTC, datetime

from core.contracts import AuditRecord, EvalResult, SilverRecord


class LoadGate:
    """100% genérico -- só decide o destino com base no resultado do Harness."""

    def __init__(self, gold_writer: Callable, audit_writer: Callable):
        self.gold_writer = gold_writer
        self.audit_writer = audit_writer

    def load(self, records: list[SilverRecord], eval_result: EvalResult) -> str:
        if eval_result.passed:
            self.gold_writer(records)
            return "gold"

        audit_records = [
            AuditRecord(
                silver_ref=record.id,
                reason=eval_result.breakdown,
                rejected_at=datetime.now(UTC).isoformat(),
                raw_content=record.transformed_content,
                metadata=record.metadata,
            )
            for record in records
        ]
        self.audit_writer(audit_records)
        return "audit"
