"""Contratos (dataclasses) trocados entre specialists, supervisors, harness e load gate.

Ver docs/ARCHITECTURE.md para o fluxo completo: Extract -> Bronze -> Transform ->
Silver -> Harness -> Load -> Gold ou Auditoria.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class BronzeRecord:
    id: str = field(default_factory=_new_id)
    source: str = ""
    raw_content: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SilverRecord:
    id: str = field(default_factory=_new_id)
    bronze_ref: str = ""
    transformed_content: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SupervisorVerdict:
    approved: bool
    details: list[str]


@dataclass
class EvalResult:
    score: float
    passed: bool
    breakdown: dict[str, float]


@dataclass
class AuditRecord:
    """O que é gravado na tabela de auditoria quando a Task 3 reprova um lote."""

    silver_ref: str
    reason: dict[str, float]
    rejected_at: str
    raw_content: Any
    metadata: dict = field(default_factory=dict)
